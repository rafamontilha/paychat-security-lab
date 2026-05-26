from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TraceStep(BaseModel):
    type: Literal[
        "thought", "tool_call", "tool_return", "final", "guard_verdict", "presidio_findings"
    ]
    content: str
    tool_name: str | None = None
    tool_args: dict | None = None
    tool_result: str | None = None
    timestamp: str = Field(default_factory=_now_iso)
    guard_categories: list[str] | None = None
    pii_entities: list[dict] | None = None
