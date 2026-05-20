from langchain_core.tools import tool
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import Order, OrderStatus, Role


def make_process_refund_tool(actor_context: dict, db: Session):
    @tool("process_refund")
    def process_refund(order_id: int) -> str:
        """Initiate a refund for a marketplace order.

        Args:
            order_id: The numeric ID of the order to refund
        """
        order = db.get(Order, order_id)
        if not order:
            return f"Order {order_id} not found."

        is_admin = actor_context["role"] == Role.admin.value
        if not is_admin and order.buyer_id != actor_context["user_id"]:
            return (
                f"Access denied: order {order_id} does not belong to you. "
                "Refunds can only be initiated by the order owner or an admin."
            )

        if order.status == OrderStatus.refunded:
            return f"Order {order_id} is already refunded."

        order.status = OrderStatus.refunded
        db.commit()
        return f"Refund initiated for order {order_id}. New status: refunded."

    return process_refund
