from langchain_core.tools import tool
from sqlalchemy.orm import Session

from app.infrastructure.defenses.tool_guard import ToolGuard
from app.infrastructure.persistence.models import Message, User


def make_send_message_tool(actor_context: dict, db: Session, guard: ToolGuard | None = None):
    @tool("send_message")
    def send_message(recipient_id: int, content: str) -> str:
        """Send a message to another user on the marketplace.

        Args:
            recipient_id: The numeric ID of the message recipient
            content: The message text to send (intentionally unsanitised — exfiltration vector)
        """
        if guard is not None:
            rejection = guard.enforce(
                "send_message", {"recipient_id": recipient_id, "content": content}, actor_context
            )
            if rejection is not None:
                return rejection

        recipient = db.get(User, recipient_id)
        if not recipient:
            return f"Recipient {recipient_id} not found."

        msg = Message(
            sender_id=actor_context["user_id"],
            recipient_id=recipient_id,
            content=content,
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return f"Message {msg.id} sent to {recipient.name} (user_id={recipient_id})."

    return send_message
