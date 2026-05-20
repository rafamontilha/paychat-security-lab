from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models import Message, User
from app.infrastructure.web.dependencies import ActorContext

router = APIRouter(prefix="/api/messages", tags=["messages"])


class MessageRequest(BaseModel):
    recipient_id: int
    content: str


class MessageOut(BaseModel):
    id: int
    sender_id: int
    recipient_id: int
    content: str

    model_config = {"from_attributes": True}


@router.post("", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def send_message(
    body: MessageRequest,
    actor: ActorContext,
    db: Session = Depends(get_db),
):
    recipient = db.get(User, body.recipient_id)
    if not recipient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient not found")

    msg = Message(
        sender_id=actor["user_id"],
        recipient_id=body.recipient_id,
        content=body.content,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg
