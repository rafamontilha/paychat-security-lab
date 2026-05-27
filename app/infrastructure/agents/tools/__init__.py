"""Tool factory — builds the 5 agent tools with actor_context injected via closure.

An optional ToolGuard (Fase 9 defense) is threaded into each tool: when present, the tool
re-validates its arguments and enforces permission boundaries before executing.
"""

from typing import Any

import chromadb
from sqlalchemy.orm import Session

from app.infrastructure.agents.tools.get_order import make_get_order_tool
from app.infrastructure.agents.tools.get_user_info import make_get_user_info_tool
from app.infrastructure.agents.tools.process_refund import make_process_refund_tool
from app.infrastructure.agents.tools.search_products import make_search_products_tool
from app.infrastructure.agents.tools.send_message import make_send_message_tool
from app.infrastructure.defenses.tool_guard import ToolGuard


def make_tools(
    actor_context: dict[str, Any],
    db: Session,
    chroma: chromadb.ClientAPI,
    guard: ToolGuard | None = None,
) -> list:
    return [
        make_search_products_tool(chroma, actor_context, guard),
        make_get_order_tool(actor_context, db, guard),
        make_process_refund_tool(actor_context, db, guard),
        make_send_message_tool(actor_context, db, guard),
        make_get_user_info_tool(actor_context, db, guard),
    ]
