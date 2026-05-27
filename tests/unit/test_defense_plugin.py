"""Unit tests for the Fase 9 plugin-defense layer.

Covers the per-role tool allow-list and the high-value-refund human-confirmation gate,
both via ToolGuard and end-to-end through the process_refund tool (with a fake DB/order).
"""

import json

from app.infrastructure.agents.tools.process_refund import make_process_refund_tool
from app.infrastructure.defenses.tool_guard import ToolGuard

# ---------------------------------------------------------------------------
# Per-role allow-list
# ---------------------------------------------------------------------------


def test_buyer_denied_get_user_info() -> None:
    rejection = ToolGuard().enforce("get_user_info", {"user_id": 5}, {"role": "buyer"})
    assert rejection is not None
    assert "tool_not_allowed_for_role:buyer" in rejection


def test_seller_denied_process_refund() -> None:
    rejection = ToolGuard().enforce("process_refund", {"order_id": 5}, {"role": "seller"})
    assert rejection is not None
    assert "tool_not_allowed_for_role:seller" in rejection


def test_buyer_allowed_process_refund() -> None:
    assert ToolGuard().enforce("process_refund", {"order_id": 5}, {"role": "buyer"}) is None


def test_support_allowed_get_user_info() -> None:
    assert ToolGuard().enforce("get_user_info", {"user_id": 5}, {"role": "support"}) is None


def test_unknown_role_denied_all_registered_tools() -> None:
    allowed, _ = ToolGuard().check_allowlist("search_products", {"role": "attacker"})
    assert allowed is False


def test_allowlist_disabled_lets_role_through() -> None:
    guard = ToolGuard(allowlist=False)
    assert guard.enforce("get_user_info", {"user_id": 5}, {"role": "buyer"}) is None


# ---------------------------------------------------------------------------
# High-value refund confirmation
# ---------------------------------------------------------------------------


def test_refund_above_threshold_requires_confirmation() -> None:
    assert ToolGuard().refund_requires_confirmation(600.0) is True


def test_refund_at_threshold_does_not_require_confirmation() -> None:
    assert ToolGuard().refund_requires_confirmation(500.0) is False


def test_refund_just_above_threshold_requires_confirmation() -> None:
    assert ToolGuard().refund_requires_confirmation(500.01) is True


def test_confirmation_disabled_never_requires() -> None:
    assert ToolGuard(human_confirmation=False).refund_requires_confirmation(9999.0) is False


# ---------------------------------------------------------------------------
# process_refund tool — confirmation gate (fake DB)
# ---------------------------------------------------------------------------


class _FakeOrder:
    def __init__(self, amount: float, buyer_id: int) -> None:
        self.amount = amount
        self.buyer_id = buyer_id
        self.status = "open"  # any sentinel != OrderStatus.refunded


class _FakeDB:
    def __init__(self, order: _FakeOrder) -> None:
        self._order = order
        self.committed = False

    def get(self, _model: object, _id: int) -> _FakeOrder:
        return self._order

    def commit(self) -> None:
        self.committed = True


def test_process_refund_returns_confirmation_for_high_value() -> None:
    db = _FakeDB(_FakeOrder(amount=800.0, buyer_id=1))
    actor = {"role": "buyer", "user_id": 1}
    tool = make_process_refund_tool(actor, db, ToolGuard())  # type: ignore[arg-type]

    result = tool.func(order_id=5)
    payload = json.loads(result)
    assert payload["requires_confirmation"] is True
    assert payload["amount"] == 800.0
    assert db.committed is False  # refund NOT applied


def test_process_refund_executes_below_threshold() -> None:
    db = _FakeDB(_FakeOrder(amount=120.0, buyer_id=1))
    actor = {"role": "buyer", "user_id": 1}
    tool = make_process_refund_tool(actor, db, ToolGuard())  # type: ignore[arg-type]

    result = tool.func(order_id=5)
    assert "Refund initiated" in result
    assert db.committed is True
