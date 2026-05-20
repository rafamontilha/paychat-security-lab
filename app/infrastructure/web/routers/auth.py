import json
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models import User
from app.infrastructure.web.dependencies import get_redis

router = APIRouter(prefix="/api/auth", tags=["auth"])

SESSION_TTL = 3600  # 1 hour


class LoginRequest(BaseModel):
    api_key: str


class LoginResponse(BaseModel):
    session_token: str
    role: str
    user_id: int
    name: str


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.api_key == body.api_key).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    token = secrets.token_hex(32)
    r = get_redis()
    r.setex(
        f"session:{token}",
        SESSION_TTL,
        json.dumps({"user_id": user.id, "role": user.role.value}),
    )
    return LoginResponse(
        session_token=token,
        role=user.role.value,
        user_id=user.id,
        name=user.name,
    )
