from langchain_core.tools import tool
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import Order, Product, Role


def make_get_order_tool(actor_context: dict, db: Session):
    @tool("get_order")
    def get_order(order_id: int) -> str:
        """Retrieve details of a marketplace order by ID.

        Args:
            order_id: The numeric ID of the order to retrieve
        """
        order = db.get(Order, order_id)
        if not order:
            return f"Order {order_id} not found."

        is_privileged = actor_context["role"] in (Role.admin.value, Role.support.value)
        if not is_privileged and order.buyer_id != actor_context["user_id"]:
            return f"Access denied: order {order_id} does not belong to you."

        product = db.get(Product, order.product_id)
        return (
            f"order_id={order.id} "
            f"status={order.status.value} "
            f"amount={float(order.amount):.2f} "
            f"product={product.title if product else '?'} "
            f"buyer_id={order.buyer_id}"
        )

    return get_order
