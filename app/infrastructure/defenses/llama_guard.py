"""Llama Guard 3 client — input safety classifier (Estágio 1 da Variante C).

Classifies user input as safe/unsafe using llama-guard-3-1b via Groq API.
Fail-closed: any connection/timeout error raises GuardUnavailableError rather than
allowing the request to pass through to the agent.
"""

import os
from dataclasses import dataclass, field

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

_GUARD_MODEL = "meta-llama/llama-guard-3-1b"
_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
_TIMEOUT = 10.0


class GuardUnavailableError(RuntimeError):
    """Raised when Llama Guard is unreachable, times out, or returns a 5xx error."""


class GuardBlockedError(RuntimeError):
    """Raised when Llama Guard classifies input as unsafe."""

    def __init__(self, category: str | None, raw_response: str) -> None:
        self.category = category
        self.raw_response = raw_response
        super().__init__(f"Input blocked by Llama Guard: {category}")


@dataclass
class GuardVerdict:
    safe: bool
    category: str | None = None
    raw_response: str = field(default="")


class LlamaGuardClient:
    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or os.environ.get("GROQ_API_KEY", "placeholder")
        self._client = OpenAI(
            base_url=_GROQ_BASE_URL,
            api_key=key,
            timeout=_TIMEOUT,
            max_retries=0,
        )

    def classify_input(self, text: str) -> GuardVerdict:
        """Classify user input. Returns GuardVerdict(safe=True) or raises GuardBlockedError.

        Raises GuardUnavailableError on network/server errors (fail-closed).
        """
        try:
            response = self._client.chat.completions.create(
                model=_GUARD_MODEL,
                messages=[{"role": "user", "content": text}],
                max_tokens=20,
                temperature=0,
            )
        except (APITimeoutError, APIConnectionError) as exc:
            raise GuardUnavailableError(f"Llama Guard unreachable: {exc}") from exc
        except APIStatusError as exc:
            if exc.status_code >= 500:
                raise GuardUnavailableError(f"Llama Guard server error {exc.status_code}: {exc}") from exc
            raise

        raw = (response.choices[0].message.content or "safe").strip()
        lines = raw.split("\n")
        is_safe = lines[0].strip().lower() == "safe"
        category = lines[1].strip() if not is_safe and len(lines) > 1 else None
        return GuardVerdict(safe=is_safe, category=category, raw_response=raw)
