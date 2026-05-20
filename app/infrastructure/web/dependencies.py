import json
import os
from typing import Annotated

import redis as redis_lib
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models import Role, User


def get_redis() -> redis_lib.Redis:
    url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    return redis_lib.from_url(url, decode_responses=True)


def get_actor_context(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    token = authorization.removeprefix("Bearer ")
    r = get_redis()
    raw = r.get(f"session:{token}")
    if not raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    data = json.loads(raw)
    user = db.get(User, data["user_id"])
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    actor = {
        "user_id": user.id,
        "role": user.role.value,
        "session_token": token,
        "name": user.name,
    }
    request.state.actor = actor
    return actor


ActorContext = Annotated[dict, Depends(get_actor_context)]


def require_roles(*roles: Role):
    def dependency(actor: ActorContext) -> dict:
        if actor["role"] not in [r.value for r in roles]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return actor

    return Depends(dependency)
