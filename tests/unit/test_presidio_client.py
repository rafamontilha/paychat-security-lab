"""Unit tests for PresidioClient — no Presidio container needed (HTTP is mocked).

Covers:
- CPF detection → redacted as <REDACTED:BR_CPF>
- PAYMENT_TOKEN detection → response blocked
- Clean text → no alterations
- INTERNAL_SECRET detection → response blocked
- Policy table: PAYMENT_TOKEN and INTERNAL_SECRET always "block"
- Presidio container down → PresidioUnavailableError
"""

from unittest.mock import MagicMock, patch

import pytest

from app.infrastructure.defenses.policy import ENTITY_POLICY
from app.infrastructure.defenses.presidio import (
    PresidioClient,
    PresidioUnavailableError,
)


def _mock_presidio_response(findings: list[dict]) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = findings
    resp.raise_for_status = MagicMock()
    return resp


@pytest.fixture
def client():
    return PresidioClient(base_url="http://localhost:3000")


# ---------------------------------------------------------------------------
# Standard PII — CPF (redact)
# ---------------------------------------------------------------------------


def test_cpf_in_text_is_redacted(client) -> None:
    text = "O CPF do usuário é 123.456.789-09 conforme cadastro."
    cpf_start = text.index("123.456.789-09")
    cpf_end = cpf_start + len("123.456.789-09")

    with patch("app.infrastructure.defenses.presidio.httpx.post") as mock_post:
        mock_post.return_value = _mock_presidio_response(
            [{"entity_type": "BR_CPF", "start": cpf_start, "end": cpf_end, "score": 0.85}]
        )
        result = client.analyze_and_redact(text)

    assert result.blocked is False
    assert "<REDACTED:BR_CPF>" in result.redacted_text
    assert "123.456.789-09" not in result.redacted_text
    assert len(result.findings) == 1


def test_clean_text_passes_through_unchanged(client) -> None:
    text = "Seu pedido foi confirmado com sucesso."
    with patch("app.infrastructure.defenses.presidio.httpx.post") as mock_post:
        mock_post.return_value = _mock_presidio_response([])
        result = client.analyze_and_redact(text)

    assert result.blocked is False
    assert result.redacted_text == text
    assert result.findings == []


# ---------------------------------------------------------------------------
# Custom recognizers — PAYMENT_TOKEN (block)
# ---------------------------------------------------------------------------


def test_payment_token_in_text_triggers_block(client) -> None:
    text = "Token de pagamento: 1234-5678-9012-3456 para a transação."
    with patch("app.infrastructure.defenses.presidio.httpx.post") as mock_post:
        mock_post.return_value = _mock_presidio_response([])
        result = client.analyze_and_redact(text)

    assert result.blocked is True
    assert (
        result.redacted_text
        == "[RESPOSTA BLOQUEADA: informação sensível detectada no output do agente]"
    )


def test_internal_secret_in_text_triggers_block(client) -> None:
    text = "Chave interna: a3f1c2d4e5b6789012345678901234ab gerada pelo sistema."
    with patch("app.infrastructure.defenses.presidio.httpx.post") as mock_post:
        mock_post.return_value = _mock_presidio_response([])
        result = client.analyze_and_redact(text)

    assert result.blocked is True


# ---------------------------------------------------------------------------
# Policy table integrity
# ---------------------------------------------------------------------------


def test_payment_token_policy_is_block() -> None:
    assert ENTITY_POLICY["PAYMENT_TOKEN"] == "block"


def test_internal_secret_policy_is_block() -> None:
    assert ENTITY_POLICY["INTERNAL_SECRET"] == "block"


def test_cpf_policy_is_redact() -> None:
    assert ENTITY_POLICY["BR_CPF"] == "redact"


def test_cnpj_policy_is_redact() -> None:
    assert ENTITY_POLICY["BR_CNPJ"] == "redact"


def test_phone_policy_is_redact() -> None:
    assert ENTITY_POLICY["PHONE_NUMBER"] == "redact"


def test_email_policy_is_redact() -> None:
    assert ENTITY_POLICY["EMAIL_ADDRESS"] == "redact"


# ---------------------------------------------------------------------------
# Recognizer threshold
# ---------------------------------------------------------------------------


def test_low_confidence_finding_is_ignored(client) -> None:
    text = "CPF do usuário: 123.456.789-09"
    cpf_start = text.index("123.456.789-09")
    cpf_end = cpf_start + len("123.456.789-09")

    with patch("app.infrastructure.defenses.presidio.httpx.post") as mock_post:
        mock_post.return_value = _mock_presidio_response(
            [{"entity_type": "BR_CPF", "start": cpf_start, "end": cpf_end, "score": 0.3}]
        )
        result = client.analyze_and_redact(text)

    assert result.blocked is False
    assert "123.456.789-09" in result.redacted_text


# ---------------------------------------------------------------------------
# Fail-closed
# ---------------------------------------------------------------------------


def test_presidio_connection_error_raises_unavailable(client) -> None:
    import httpx

    with patch("app.infrastructure.defenses.presidio.httpx.post") as mock_post:
        mock_post.side_effect = httpx.ConnectError("connection refused")
        with pytest.raises(PresidioUnavailableError):
            client.analyze_and_redact("some text")


def test_presidio_timeout_raises_unavailable(client) -> None:
    import httpx

    with patch("app.infrastructure.defenses.presidio.httpx.post") as mock_post:
        mock_post.side_effect = httpx.ReadTimeout("timeout")
        with pytest.raises(PresidioUnavailableError):
            client.analyze_and_redact("some text")
