"""Unit tests for the Fase 9 disclosure layer (data classification + policy)."""

from app.infrastructure.defenses.data_classifier import DataClass, DataClassifier
from app.infrastructure.defenses.pipeline import DefenseConfig, DefensePipeline

# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def test_classify_internal_secret_as_secret() -> None:
    text = "a chave interna é a3f1c2d4e5b6789012345678901234ab"
    assert DataClassifier().classify(text) is DataClass.secret


def test_classify_payment_token_as_secret() -> None:
    assert DataClassifier().classify("token 1234-5678-9012-3456") is DataClass.secret


def test_classify_password_assignment_as_secret() -> None:
    assert DataClassifier().classify("password: hunter2value") is DataClass.secret


def test_classify_cpf_as_pii() -> None:
    assert DataClassifier().classify("CPF 123.456.789-09 do cliente") is DataClass.pii


def test_classify_email_as_pii() -> None:
    assert DataClassifier().classify("contato: joao@example.com") is DataClass.pii


def test_classify_system_prompt_mention_as_internal() -> None:
    assert DataClassifier().classify("minhas instruções no system prompt") is DataClass.internal


def test_classify_benign_as_public() -> None:
    assert DataClassifier().classify("seu pedido foi confirmado") is DataClass.public


# ---------------------------------------------------------------------------
# Policy application
# ---------------------------------------------------------------------------


def test_apply_blocks_secret() -> None:
    out, label, action = DataClassifier().apply("segredo a3f1c2d4e5b6789012345678901234ab")
    assert label is DataClass.secret
    assert action == "block"
    assert "BLOQUEADA" in out


def test_apply_redacts_pii() -> None:
    out, label, action = DataClassifier().apply("email joao@example.com")
    assert label is DataClass.pii
    assert action == "redact"
    assert "<REDACTED:PII>" in out
    assert "joao@example.com" not in out


def test_apply_allows_public() -> None:
    out, label, action = DataClassifier().apply("tudo certo com seu pedido")
    assert label is DataClass.public
    assert action == "allow"
    assert out == "tudo certo com seu pedido"


# ---------------------------------------------------------------------------
# Pipeline integration
# ---------------------------------------------------------------------------


def _pipeline() -> DefensePipeline:
    return DefensePipeline(
        DefenseConfig(canary=False, presidio_output=False, data_classification=True)
    )


def test_pipeline_blocks_secret_via_disclosure() -> None:
    final, reasons = _pipeline().apply_output_defenses("key a3f1c2d4e5b6789012345678901234ab")
    assert "disclosure_block:secret" in reasons
    assert "a3f1c2d4e5b6789012345678901234ab" not in final


def test_pipeline_redacts_pii_via_disclosure() -> None:
    final, reasons = _pipeline().apply_output_defenses("o email é joao@example.com")
    assert "disclosure_redact:pii" in reasons
    assert "<REDACTED:PII>" in final


def test_pipeline_disclosure_disabled_passes_through() -> None:
    pipeline = DefensePipeline(
        DefenseConfig(canary=False, presidio_output=False, data_classification=False)
    )
    final, reasons = pipeline.apply_output_defenses("email joao@example.com")
    assert final == "email joao@example.com"
    assert reasons == []
