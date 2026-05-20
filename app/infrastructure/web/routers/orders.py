from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models import Order, Role
from app.infrastructure.web.dependencies import ActorContext

router = APIRouter(prefix="/api/orders", tags=["orders"])


class OrderOut(BaseModel):
    id: int
    buyer_id: int
    product_id: int
    status: str
    amount: float

    model_config = {"from_attributes": True}


@router.get("", response_model=list[OrderOut])
def list_orders(actor: ActorContext, db: Session = Depends(get_db)):
    q = db.query(Order)
    if actor["role"] not in (Role.admin.value, Role.support.value):
        q = q.filter(Order.buyer_id == actor["user_id"])
    return q.all()


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, actor: ActorContext, db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if actor["role"] not in (Role.admin.value, Role.support.value):
        if order.buyer_id != actor["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
    return order
