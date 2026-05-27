"""Disclosure layer: classify agent output by sensitivity and apply a disposal policy.

Defense-in-depth on top of Presidio. Even when upstream redaction misses something, the
classifier labels the response by its most sensitive content (public < internal < pii <
secret) and applies DATA_CLASS_POLICY: secrets block the whole response, PII is redacted,
internal/public pass through. Heuristic and language-agnostic (regex over BR PII + secret
markers) so it adds a cheap, independent gate before the response reaches the user.
"""

import re
from enum import Enum

from app.infrastructure.defenses.policy import BLOCKED_RESPONSE, DATA_CLASS_POLICY


class DataClass(str, Enum):
    public = "public"
    internal = "internal"
    pii = "pii"
    secret = "secret"


_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b[0-9a-f]{32}\b"),  # INTERNAL_SECRET (secrets.token_hex(16))
    re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{4}\b"),  # PAYMENT_TOKEN
    re.compile(r"\b(sk|pk)[-_][A-Za-z0-9]{8,}", re.I),  # API-key-style tokens
    re.compile(r"(senha|password|secret|api[_-]?key|token)\s*[:=]\s*\S+", re.I),
    re.compile(r"\bbearer\s+[A-Za-z0-9._-]{8,}", re.I),
)

_PII_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),  # CPF
    re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"),  # CNPJ
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),  # email
    re.compile(r"\(?\d{2}\)?\s?9?\d{4}-?\d{4}\b"),  # BR phone
)

_INTERNAL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(system\s+prompt|actor_context|audit_log|session_token)\b", re.I),
)


class DataClassifier:
    def classify(self, text: str) -> DataClass:
        if any(p.search(text) for p in _SECRET_PATTERNS):
            return DataClass.secret
        if any(p.search(text) for p in _PII_PATTERNS):
            return DataClass.pii
        if any(p.search(text) for p in _INTERNAL_PATTERNS):
            return DataClass.internal
        return DataClass.public

    def apply(self, text: str) -> tuple[str, DataClass, str]:
        """Classify and dispose. Returns (output_text, label, action)."""
        label = self.classify(text)
        action = DATA_CLASS_POLICY.get(label.value, "allow")
        if action == "block":
            return BLOCKED_RESPONSE, label, action
        if action == "redact":
            return self._redact_pii(text), label, action
        return text, label, action

    @staticmethod
    def _redact_pii(text: str) -> str:
        result = text
        for pattern in _PII_PATTERNS:
            result = pattern.sub("<REDACTED:PII>", result)
        return result
