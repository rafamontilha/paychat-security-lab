import json

import chromadb
import redis as redis_lib
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.domain.entities.agent_trace import TraceStep
from app.infrastructure.defenses.llama_guard import GuardBlockedError, GuardUnavailableError
from app.infrastructure.defenses.presidio import PresidioUnavailableError
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models import User
from app.infrastructure.rag.client import get_chroma_client
from app.infrastructure.web.dependencies import get_redis

router = APIRouter(prefix="/api/agent", tags=["agent"])

_VALID_VARIANTS = {"a", "b", "c"}


class AgentChatRequest(BaseModel):
    session_token: str
    message: str


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


@router.post("/chat", response_model=AgentChatResponse)
def agent_chat(
    body: AgentChatRequest,
    variant: str = Query(default="a"),
    x_variant: str | None = Header(default=None),
    db: Session = Depends(get_db),
    chroma: chromadb.ClientAPI = Depends(get_chroma_client),
) -> AgentChatResponse:
    effective_variant = x_variant if x_variant is not None else variant

    if effective_variant not in _VALID_VARIANTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown variant '{effective_variant}'. Valid: {sorted(_VALID_VARIANTS)}",
        )

    redis_client = get_redis()
    actor_context = _resolve_actor(body.session_token, redis_client, db)

    if effective_variant == "a":
        from app.infrastructure.agents.variant_a_claude import VariantAClaude

        agent: object = VariantAClaude(
            actor_context=actor_context,
            db=db,
            chroma=chroma,
            redis_client=redis_client,
        )
    elif effective_variant == "b":
        from app.infrastructure.agents.variant_b_llama import VariantBLlama

        agent = VariantBLlama(
            actor_context=actor_context,
            db=db,
            chroma=chroma,
            redis_client=redis_client,
        )
    else:
        from app.infrastructure.agents.variant_c_pipeline import VariantCPipeline

        agent = VariantCPipeline(
            actor_context=actor_context,
            db=db,
            chroma=chroma,
            redis_client=redis_client,
        )

    try:
        response, trace = agent.run(body.message)  # type: ignore[union-attr]
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
