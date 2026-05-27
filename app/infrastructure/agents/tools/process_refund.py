import json

from langchain_core.tools import tool
from sqlalchemy.orm import Session

from app.infrastructure.defenses.tool_guard import REFUND_CONFIRMATION_THRESHOLD, ToolGuard
from app.infrastructure.persistence.models import Order, OrderStatus, Role


def make_process_refund_tool(actor_context: dict, db: Session, guard: ToolGuard | None = None):
    @tool("process_refund")
    def process_refund(order_id: int) -> str:
        """Initiate a refund for a marketplace order.

        Args:
            order_id: The numeric ID of the order to refund
        """
        if guard is not None:
            rejection = guard.enforce("process_refund", {"order_id": order_id}, actor_context)
            if rejection is not None:
                return rejection

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

        # Plugin-layer defense: high-value refunds require human confirmation rather than
        # executing autonomously. The refund is NOT applied; the agent must surface this.
        amount = float(order.amount)
        if guard is not None and guard.refund_requires_confirmation(amount):
            return json.dumps(
                {
                    "requires_confirmation": True,
                    "reason": "high_value_refund",
                    "order_id": order_id,
                    "amount": round(amount, 2),
                    "threshold": REFUND_CONFIRMATION_THRESHOLD,
                    "message": (
                        f"Refund of R$ {amount:.2f} exceeds the R$ "
                        f"{REFUND_CONFIRMATION_THRESHOLD:.0f} auto-approval limit and "
                        "requires human confirmation before it can be processed."
                    ),
                }
            )

        order.status = OrderStatus.refunded
        db.commit()
        return f"Refund initiated for order {order_id}. New status: refunded."

    return process_refund
