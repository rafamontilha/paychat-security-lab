"""Domain model for red-team evidence records."""

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Literal

from pydantic import BaseModel, Field


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class EvidenceRecord(BaseModel):
    id: str
    timestamp: str = Field(default_factory=_now_iso)
    variant: Literal["a", "b", "c"]
    category: Literal["pi_direct", "pi_indirect", "ioh"]
    technique: str
    payload: str
    temperature: float
    run_index: int
    response: str
    success_flag: bool
    success_reason: str
    execution_status: Literal["success", "error", "max_iterations"]
    trace: list[dict[str, Any]]

    @staticmethod
    def make_id(
        variant: str,
        category: str,
        technique: str,
        payload: str,
        temperature: float,
        run_index: int,
    ) -> str:
        raw = f"{variant}|{category}|{technique}|{payload}|{temperature}|{run_index}"
        return sha256(raw.encode()).hexdigest()[:16]
