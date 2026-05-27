import json

import chromadb
import redis as redis_lib
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.domain.entities.agent_trace import TraceStep
from app.infrastructure.defenses.llama_guard import GuardBlockedError, GuardUnavailableError
from app.infrastructure.defenses.pipeline import DefenseInputBlocked, DefensePipeline
from app.infrastructure.defenses.presidio import PresidioUnavailableError
from app.infrastructure.defenses.rate_limiter import AntiTheftGuard
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models import User
from app.infrastructure.rag.client import get_chroma_client
from app.infrastructure.web.dependencies import get_redis

router = APIRouter(prefix="/api/agent", tags=["agent"])

_VALID_VARIANTS = {"a", "b", "c"}


class AgentChatRequest(BaseModel):
    session_token: str
    message: str
    temperature: float = 0.0


class AgentChatResponse(BaseModel):
    response: str
    trace: list[TraceStep]
    session_token: str


def _resolve_actor(
    session_token: str,
    redis_client: redis_lib.Redis,
    db: Session,
) -> dict:
    raw = redis_client.get(f"session:{session_token}")
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token",
        )
    assert isinstance(raw, (str, bytes, bytearray))
    data = json.loads(raw)
    user = db.get(User, data["user_id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return {
        "user_id": user.id,
        "role": user.role.value,
        "session_token": session_token,
        "name": user.name,
    }


def _parse_toggle(value: str | None) -> bool:
    return value is not None and value.lower() in {"on", "true", "1", "yes"}


@router.post("/chat", response_model=AgentChatResponse)
def agent_chat(
    body: AgentChatRequest,
    variant: str = Query(default="a"),
    defense: str = Query(default="off"),
    x_variant: str | None = Header(default=None),
    x_defense: str | None = Header(default=None),
    db: Session = Depends(get_db),
    chroma: chromadb.ClientAPI = Depends(get_chroma_client),
) -> AgentChatResponse:
    effective_variant = x_variant if x_variant is not None else variant

    if effective_variant not in _VALID_VARIANTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown variant '{effective_variant}'. Valid: {sorted(_VALID_VARIANTS)}",
        )

    defense_enabled = _parse_toggle(x_defense) if x_defense is not None else _parse_toggle(defense)

    redis_client = get_redis()
    actor_context = _resolve_actor(body.session_token, redis_client, db)

    # Variants A and B receive the opt-in defense pipeline by construction (ADR-001).
    # Variant C keeps its own multi-model pipeline and ignores this flag.
    defense_pipeline = (
        DefensePipeline() if defense_enabled and effective_variant in {"a", "b"} else None
    )

    if effective_variant == "a":
        from app.infrastructure.agents.variant_a_claude import VariantAClaude

        agent: object = VariantAClaude(
            actor_context=actor_context,
            db=db,
            chroma=chroma,
            redis_client=redis_client,
            temperature=body.temperature,
            defense=defense_pipeline,
        )
    elif effective_variant == "b":
        from app.infrastructure.agents.variant_b_llama import VariantBLlama

        agent = VariantBLlama(
            actor_context=actor_context,
            db=db,
            chroma=chroma,
            redis_client=redis_client,
            temperature=body.temperature,
            defense=defense_pipeline,
        )
    else:
        from app.infrastructure.agents.variant_c_pipeline import VariantCPipeline

        agent = VariantCPipeline(
            actor_context=actor_context,
            db=db,
            chroma=chroma,
            redis_client=redis_client,
            temperature=body.temperature,
        )

    # Anti-theft layer (rate limit + query-budget probing) runs before the agent for A/B
    # when defenses are enabled. Variant C is unaffected (keeps its own pipeline).
    if defense_pipeline is not None:
        allowed, reason = AntiTheftGuard(redis_client).check(body.session_token, body.message)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"error": "anti_theft_blocked", "reason": reason},
            )

    try:
        response, trace = agent.run(body.message)  # type: ignore[attr-defined]
    except DefenseInputBlocked as exc:
        defense_trace = [TraceStep(type="defense_verdict", content=f"input_blocked:{exc.reason}")]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "blocked_by_defense",
                "category": exc.reason,
                "trace": [step.model_dump() for step in defense_trace],
            },
        )
    except GuardBlockedError as exc:
        guard_trace = [
            TraceStep(
                type="guard_verdict",
                content=f"unsafe:{exc.category}",
                guard_categories=[exc.category] if exc.category else [],
            )
        ]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "blocked_by_guard",
                "category": exc.category,
                "trace": [step.model_dump() for step in guard_trace],
            },
        )
    except (GuardUnavailableError, PresidioUnavailableError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "pipeline_stage_unavailable", "message": str(exc)},
        )

    return AgentChatResponse(
        response=response,
        trace=trace,
        session_token=body.session_token,
    )
