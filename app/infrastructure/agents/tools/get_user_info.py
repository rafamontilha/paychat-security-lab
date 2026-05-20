from langchain_core.tools import tool
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import Role, User


def make_get_user_info_tool(actor_context: dict, db: Session):
    @tool("get_user_info")
    def get_user_info(user_id: int) -> str:
        """Retrieve user details by ID. Restricted to support and admin roles.

        Args:
            user_id: The numeric ID of the user to look up
        """
        allowed_roles = (Role.support.value, Role.admin.value)
        if actor_context["role"] not in allowed_roles:
            return (
                "Access denied: get_user_info requires support or admin role. "
                f"Your current role is '{actor_context['role']}'."
            )

        user = db.get(User, user_id)
        if not user:
            return f"User {user_id} not found."

        return (
            f"user_id={user.id} name={user.name} role={user.role.value} "
            f"email={user.email} cpf={user.cpf}"
        )

    return get_user_info
