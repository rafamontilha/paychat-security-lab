"""Tool-call guard — schema re-validation (output layer) + permission boundaries (plugin layer).

Output layer (Fase 9): re-validate tool-call arguments against explicit Pydantic schemas
before execution — positive IDs, bounded content length — rejecting malformed calls with a
structured message returned to the agent instead of letting them hit the database.

Sandboxing note: actor_context (role, user_id, session_token) is injected into each tool by
the runtime via closure and is never a tool parameter. The model cannot set or override it,
so the guard reasons about the model-supplied args only, with the trusted actor_context
passed separately by the runtime.

(The plugin layer extends `enforce` with a per-role allow-list and human-confirmation for
high-value refunds.)
"""

from typing import Any

from pydantic import BaseModel, Field, ValidationError

_REJECTION_PREFIX = "[DEFENSE] tool call rejected"


class _GetOrderArgs(BaseModel):
    order_id: int | None = Field(default=None, ge=0)


class _ProcessRefundArgs(BaseModel):
    order_id: int = Field(gt=0)


class _SendMessageArgs(BaseModel):
    recipient_id: int = Field(gt=0)
    content: str = Field(min_length=1, max_length=2000)


class _GetUserInfoArgs(BaseModel):
    user_id: int = Field(gt=0)


class _SearchProductsArgs(BaseModel):
    query: str = Field(min_length=1, max_length=500)


_ARG_SCHEMAS: dict[str, type[BaseModel]] = {
    "get_order": _GetOrderArgs,
    "process_refund": _ProcessRefundArgs,
    "send_message": _SendMessageArgs,
    "get_user_info": _GetUserInfoArgs,
    "search_products": _SearchProductsArgs,
}

# Per-role tool allow-list (plugin layer). Defense-in-depth on top of each tool's own RBAC:
# a tool a role should never invoke is denied by the guard before any DB access. Sellers do
# not initiate refunds; only support/admin look up arbitrary users.
_ALL_TOOLS = frozenset(_ARG_SCHEMAS)
_ROLE_TOOL_ALLOWLIST: dict[str, frozenset[str]] = {
    "buyer": frozenset({"search_products", "get_order", "process_refund", "send_message"}),
    "seller": frozenset({"search_products", "get_order", "send_message"}),
    "support": _ALL_TOOLS,
    "admin": _ALL_TOOLS,
}

# Destructive refunds above this BRL amount require human confirmation (excessive-agency guard).
REFUND_CONFIRMATION_THRESHOLD = 500.0


class ToolGuard:
    def __init__(
        self,
        schema_validation: bool = True,
        allowlist: bool = True,
        human_confirmation: bool = True,
    ) -> None:
        self._schema_validation = schema_validation
        self._allowlist = allowlist
        self._human_confirmation = human_confirmation

    def validate_args(self, tool_name: str, args: dict[str, Any]) -> tuple[bool, str]:
        """Return (valid, reason). Unknown tools pass (no schema registered)."""
        schema = _ARG_SCHEMAS.get(tool_name)
        if schema is None:
            return True, "no_schema"
        try:
            schema(**args)
        except ValidationError as exc:
            errors = "; ".join(
                f"{e['loc'][0] if e['loc'] else '?'}:{e['type']}" for e in exc.errors()
            )
            return False, f"schema_violation:{errors}"
        return True, "valid"

    def check_allowlist(self, tool_name: str, actor_context: dict[str, Any]) -> tuple[bool, str]:
        """Return (allowed, reason). A role may only call tools on its allow-list."""
        role = actor_context.get("role", "")
        allowed_tools = _ROLE_TOOL_ALLOWLIST.get(role, frozenset())
        if tool_name in _ARG_SCHEMAS and tool_name not in allowed_tools:
            return False, f"tool_not_allowed_for_role:{role}"
        return True, "allowed"

    def refund_requires_confirmation(self, amount: float) -> bool:
        """True if a refund of this amount needs human confirmation before executing."""
        return self._human_confirmation and amount > REFUND_CONFIRMATION_THRESHOLD

    def enforce(
        self, tool_name: str, args: dict[str, Any], actor_context: dict[str, Any]
    ) -> str | None:
        """Run guard checks before a tool executes.

        Returns a rejection string to short-circuit the tool (returned to the agent as the
        tool result), or None to let the tool proceed. The high-value-refund confirmation is
        applied inside process_refund itself, which has the order amount.
        """
        if self._schema_validation:
            valid, reason = self.validate_args(tool_name, args)
            if not valid:
                return f"{_REJECTION_PREFIX} ({tool_name}): {reason}"
        if self._allowlist:
            allowed, reason = self.check_allowlist(tool_name, actor_context)
            if not allowed:
                return f"{_REJECTION_PREFIX} ({tool_name}): {reason}"
        return None
