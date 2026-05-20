from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models import Role, User
from app.infrastructure.web.dependencies import require_roles

router = APIRouter(prefix="/api/users", tags=["users"])

_support_or_admin = require_roles(Role.support, Role.admin)


class UserOut(BaseModel):
    id: int
    name: str
    cpf: str
    email: str
    phone: str
    role: str

    model_config = {"from_attributes": True}


@router.get("/{user_id}", response_model=UserOut, dependencies=[_support_or_admin])
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
