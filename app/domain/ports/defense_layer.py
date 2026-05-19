from typing import Protocol, runtime_checkable


@runtime_checkable
class DefenseLayer(Protocol):
    async def check_input(self, text: str) -> tuple[bool, str]:
        """Return (allowed, reason). allowed=False blocks the request."""
        ...

    async def filter_output(self, text: str) -> str:
        """Return the (potentially redacted) output text."""
        ...
