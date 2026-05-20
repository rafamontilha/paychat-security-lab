from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models import Order, OrderStatus, Role
from app.infrastructure.web.dependencies import ActorContext

router = APIRouter(prefix="/api/refunds", tags=["refunds"])


class RefundRequest(BaseModel):
    order_id: int


class RefundOut(BaseModel):
    order_id: int
    status: str
    message: str


@router.post("", response_model=RefundOut)
def request_refund(
    body: RefundRequest,
    actor: ActorContext,
    db: Session = Depends(get_db),
):
    order = db.get(Order, body.order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    is_admin = actor["role"] == Role.admin.value
    if not is_admin and order.buyer_id != actor["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )

    if order.status == OrderStatus.refunded:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Order already refunded")

    order.status = OrderStatus.refunded
    db.commit()
    return RefundOut(order_id=order.id, status="refunded", message="Refund initiated")
