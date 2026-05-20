"""Tool factory — builds the 5 agent tools with actor_context injected via closure."""

from typing import Any

import chromadb
from sqlalchemy.orm import Session

from app.infrastructure.agents.tools.get_order import make_get_order_tool
from app.infrastructure.agents.tools.get_user_info import make_get_user_info_tool
from app.infrastructure.agents.tools.process_refund import make_process_refund_tool
from app.infrastructure.agents.tools.search_products import make_search_products_tool
from app.infrastructure.agents.tools.send_message import make_send_message_tool


def make_tools(actor_context: dict[str, Any], db: Session, chroma: chromadb.ClientAPI) -> list:
    return [
        make_search_products_tool(chroma),
        make_get_order_tool(actor_context, db),
        make_process_refund_tool(actor_context, db),
        make_send_message_tool(actor_context, db),
        make_get_user_info_tool(actor_context, db),
    ]
