import json

import chromadb
import redis as redis_lib
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.domain.entities.agent_trace import TraceStep
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models import User
from app.infrastructure.rag.client import get_chroma_client
from app.infrastructure.web.dependencies import get_redis

router = APIRouter(prefix="/api/agent", tags=["agent"])


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
    db: Session = Depends(get_db),
    chroma: chromadb.ClientAPI = Depends(get_chroma_client),
) -> AgentChatResponse:
    redis_client = get_redis()
    actor_context = _resolve_actor(body.session_token, redis_client, db)

    from app.infrastructure.agents.variant_a_claude import VariantAClaude

    agent = VariantAClaude(
        actor_context=actor_context,
        db=db,
        chroma=chroma,
        redis_client=redis_client,
    )
    response, trace = agent.run(body.message)
    return AgentChatResponse(
        response=response,
        trace=trace,
        session_token=body.session_token,
    )
