"""Unit tests for the Fase 9 output-defense layer.

Covers ToolGuard Pydantic argument re-validation and the DefensePipeline output path with
Presidio wired in (Presidio client injected — no container needed).
"""

from app.infrastructure.defenses.pipeline import DefenseConfig, DefensePipeline
from app.infrastructure.defenses.presidio import PresidioFinding, RedactionResult
from app.infrastructure.defenses.tool_guard import ToolGuard

# ---------------------------------------------------------------------------
# ToolGuard — argument re-validation
# ---------------------------------------------------------------------------


def test_get_order_accepts_valid_id() -> None:
    valid, _ = ToolGuard().validate_args("get_order", {"order_id": 5})
    assert valid is True


def test_get_order_accepts_none_for_latest() -> None:
    valid, _ = ToolGuard().validate_args("get_order", {"order_id": None})
    assert valid is True


def test_get_order_rejects_negative_id() -> None:
    valid, reason = ToolGuard().validate_args("get_order", {"order_id": -1})
    assert valid is False
    assert reason.startswith("schema_violation")


def test_process_refund_rejects_zero_id() -> None:
    valid, _ = ToolGuard().validate_args("process_refund", {"order_id": 0})
    assert valid is False


def test_process_refund_accepts_positive_id() -> None:
    valid, _ = ToolGuard().validate_args("process_refund", {"order_id": 42})
    assert valid is True


def test_send_message_rejects_empty_content() -> None:
    valid, _ = ToolGuard().validate_args("send_message", {"recipient_id": 3, "content": ""})
    assert valid is False


def test_send_message_rejects_oversized_content() -> None:
    valid, _ = ToolGuard().validate_args("send_message", {"recipient_id": 3, "content": "x" * 2001})
    assert valid is False


def test_send_message_accepts_valid() -> None:
    valid, _ = ToolGuard().validate_args(
        "send_message", {"recipient_id": 3, "content": "olá, tudo bem?"}
    )
    assert valid is True


def test_get_user_info_rejects_zero_id() -> None:
    valid, _ = ToolGuard().validate_args("get_user_info", {"user_id": 0})
    assert valid is False


def test_search_products_rejects_empty_query() -> None:
    valid, _ = ToolGuard().validate_args("search_products", {"query": ""})
    assert valid is False


def test_unknown_tool_passes() -> None:
    valid, reason = ToolGuard().validate_args("unknown_tool", {"x": 1})
    assert valid is True
    assert reason == "no_schema"


def test_enforce_returns_rejection_on_invalid() -> None:
    rejection = ToolGuard().enforce("process_refund", {"order_id": -5}, {"role": "buyer"})
    assert rejection is not None
    assert rejection.startswith("[DEFENSE] tool call rejected")


def test_enforce_returns_none_on_valid() -> None:
    assert ToolGuard().enforce("process_refund", {"order_id": 7}, {"role": "buyer"}) is None


# ---------------------------------------------------------------------------
# DefensePipeline output path with Presidio
# ---------------------------------------------------------------------------


class _FakePresidio:
    def __init__(self, result: RedactionResult) -> None:
        self._result = result

    def analyze_and_redact(self, text: str) -> RedactionResult:
        return self._result


def test_filter_output_redacts_via_presidio() -> None:
    redacted = RedactionResult(
        redacted_text="CPF: <REDACTED:BR_CPF>",
        findings=[PresidioFinding("BR_CPF", 5, 19, 0.9)],
        blocked=False,
    )
    pipeline = DefensePipeline(
        DefenseConfig(canary=False, presidio_output=True),
        presidio_client=_FakePresidio(redacted),  # type: ignore[arg-type]
    )
    assert pipeline.filter_output("CPF: 123.456.789-09") == "CPF: <REDACTED:BR_CPF>"


def test_filter_output_disabled_passes_through() -> None:
    pipeline = DefensePipeline(DefenseConfig(canary=False, presidio_output=False))
    assert pipeline.filter_output("CPF: 123.456.789-09") == "CPF: 123.456.789-09"


def test_apply_output_defenses_marks_filtered() -> None:
    redacted = RedactionResult(
        redacted_text="<REDACTED:EMAIL_ADDRESS>",
        findings=[PresidioFinding("EMAIL_ADDRESS", 0, 5, 0.9)],
        blocked=False,
    )
    pipeline = DefensePipeline(
        DefenseConfig(canary=False, presidio_output=True),
        presidio_client=_FakePresidio(redacted),  # type: ignore[arg-type]
    )
    final, reasons = pipeline.apply_output_defenses("a@b.com")
    assert final == "<REDACTED:EMAIL_ADDRESS>"
    assert "output_filtered" in reasons


def test_tool_guard_built_when_schema_validation_enabled() -> None:
    pipeline = DefensePipeline(DefenseConfig(schema_validation=True, presidio_output=False))
    assert pipeline.tool_guard is not None


def test_tool_guard_absent_when_all_guard_flags_disabled() -> None:
    pipeline = DefensePipeline(
        DefenseConfig(
            schema_validation=False,
            tool_allowlist=False,
            human_confirmation=False,
            presidio_output=False,
        )
    )
    assert pipeline.tool_guard is None
