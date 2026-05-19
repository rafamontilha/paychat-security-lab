from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AgentRuntime(Protocol):
    async def run(
        self,
        session_token: str,
        message: str,
        actor_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute one turn of the ReAct loop.

        Returns a dict with at least 'response' (str) and 'trace' (list).
        """
        ...
