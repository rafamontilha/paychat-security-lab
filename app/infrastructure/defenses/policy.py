"""PII entity → action policy for Variant C output filtering.

ENTITY_POLICY maps Presidio entity types (including custom ones) to a disposal action:
- "redact": replace the span with <REDACTED:TYPE> in the response
- "block": block the entire response and return a safe placeholder

Thresholds are the minimum confidence score (0.0–1.0) required to act.
"""

from typing import Literal

ENTITY_POLICY: dict[str, Literal["redact", "block"]] = {
    "BR_CPF": "redact",
    "BR_CNPJ": "redact",
    "PHONE_NUMBER": "redact",
    "EMAIL_ADDRESS": "redact",
    "PAYMENT_TOKEN": "block",
    "INTERNAL_SECRET": "block",
}

RECOGNIZER_THRESHOLD = 0.5

BLOCKED_RESPONSE = "[RESPOSTA BLOQUEADA: informação sensível detectada no output do agente]"
