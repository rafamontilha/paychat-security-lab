"""Presidio Analyzer client — output PII filter (Estágio 3 da Variante C).

Detects PII in agent output using:
1. Presidio Analyzer HTTP API (Brazilian entities: CPF, CNPJ, phone, email)
2. Local regex recognizers for custom entities: PAYMENT_TOKEN and INTERNAL_SECRET

Applies policy from policy.py: "redact" replaces span with <REDACTED:TYPE>,
"block" marks the entire response as blocked.

Fail-closed: connection errors raise PresidioUnavailableError.

PAYMENT_TOKEN pattern: 4 groups of 4 digits separated by dashes (seed _format_card output).
INTERNAL_SECRET pattern: 32-char lowercase hex string (seed secrets.token_hex(16) output).
"""

import os
import re
from dataclasses import dataclass, field

import httpx

from app.infrastructure.defenses.policy import (
    BLOCKED_RESPONSE,
    ENTITY_POLICY,
    RECOGNIZER_THRESHOLD,
)

_DEFAULT_PRESIDIO_URL = "http://presidio:3000"
_TIMEOUT = 5.0

_CUSTOM_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("PAYMENT_TOKEN", re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{4}\b")),
    ("INTERNAL_SECRET", re.compile(r"\b[0-9a-f]{32}\b")),
]

_PRESIDIO_ENTITIES = ["BR_CPF", "BR_CNPJ", "PHONE_NUMBER", "EMAIL_ADDRESS"]


class PresidioUnavailableError(RuntimeError):
    """Raised when the Presidio Analyzer container is unreachable."""


@dataclass
class PresidioFinding:
    entity_type: str
    start: int
    end: int
    score: float
    text: str = field(default="")


@dataclass
class RedactionResult:
    redacted_text: str
    findings: list[PresidioFinding]
    blocked: bool


class PresidioClient:
    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = (base_url or os.environ.get("PRESIDIO_URL", _DEFAULT_PRESIDIO_URL)).rstrip(
            "/"
        )

    def analyze_and_redact(self, text: str) -> RedactionResult:
        """Analyze text for PII and apply policy (redact or block).

        Raises PresidioUnavailableError on connection errors (fail-closed).
        """
        presidio_findings = self._call_presidio(text)
        custom_findings = self._run_custom_recognizers(text)

        all_findings = _merge_findings(presidio_findings + custom_findings)
        all_findings = [f for f in all_findings if f.score >= RECOGNIZER_THRESHOLD]

        if not all_findings:
            return RedactionResult(redacted_text=text, findings=[], blocked=False)

        for finding in all_findings:
            action = ENTITY_POLICY.get(finding.entity_type)
            if action == "block":
                return RedactionResult(
                    redacted_text=BLOCKED_RESPONSE,
                    findings=all_findings,
                    blocked=True,
                )

        redacted = _apply_redactions(text, all_findings)
        return RedactionResult(redacted_text=redacted, findings=all_findings, blocked=False)

    def _call_presidio(self, text: str) -> list[PresidioFinding]:
        try:
            response = httpx.post(
                f"{self._base_url}/analyze",
                json={"text": text, "language": "pt", "entities": _PRESIDIO_ENTITIES},
                timeout=_TIMEOUT,
            )
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise PresidioUnavailableError(f"Presidio unreachable: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise PresidioUnavailableError(f"Presidio timeout: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code >= 500:
                raise PresidioUnavailableError(
                    f"Presidio server error {exc.response.status_code}"
                ) from exc
            raise

        findings = []
        for item in response.json():
            entity_type = item.get("entity_type", "")
            if entity_type in ENTITY_POLICY:
                start = item["start"]
                end = item["end"]
                findings.append(
                    PresidioFinding(
                        entity_type=entity_type,
                        start=start,
                        end=end,
                        score=float(item.get("score", 1.0)),
                        text=text[start:end],
                    )
                )
        return findings

    def _run_custom_recognizers(self, text: str) -> list[PresidioFinding]:
        findings = []
        for entity_type, pattern in _CUSTOM_PATTERNS:
            for match in pattern.finditer(text):
                findings.append(
                    PresidioFinding(
                        entity_type=entity_type,
                        start=match.start(),
                        end=match.end(),
                        score=1.0,
                        text=match.group(),
                    )
                )
        return findings


def _merge_findings(findings: list[PresidioFinding]) -> list[PresidioFinding]:
    """Sort by position and remove overlapping spans (keep highest score)."""
    if not findings:
        return []
    findings = sorted(findings, key=lambda f: (f.start, -f.score))
    merged: list[PresidioFinding] = [findings[0]]
    for f in findings[1:]:
        if f.start < merged[-1].end:
            if f.score > merged[-1].score:
                merged[-1] = f
        else:
            merged.append(f)
    return merged


def _apply_redactions(text: str, findings: list[PresidioFinding]) -> str:
    """Replace finding spans with <REDACTED:TYPE> markers, right-to-left."""
    result = text
    for f in sorted(findings, key=lambda x: x.start, reverse=True):
        result = result[: f.start] + f"<REDACTED:{f.entity_type}>" + result[f.end :]
    return result
