from typing import Protocol, runtime_checkable

from app.domain.entities.evidence import Evidence


@runtime_checkable
class EvidenceStore(Protocol):
    async def save(self, evidence: Evidence) -> str:
        """Persist evidence and return its ID."""
        ...

    async def load(self, evidence_id: str) -> Evidence: ...

    async def list_by_category(self, category: str) -> list[Evidence]: ...
