"""Safety classifier client — Estágio 1 da Variante C.

Uses Llama Guard 4 via Together AI (OpenAI-compatible API).
The model returns "safe" for benign inputs or "unsafe\nS{category}" for unsafe inputs.

Detection: response starts with "unsafe" (case-insensitive).
Fail-closed: connection/timeout errors raise GuardUnavailableError.
"""

import os
from dataclasses import dataclass, field

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

_GUARD_MODEL = os.environ.get("LLM_GUARD_MODEL", "meta-llama/Llama-Guard-4-12B")
_LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.together.xyz/v1")
_TIMEOUT = 15.0
_MAX_TOKENS = 20  # "unsafe\nS4" is ~5 tokens; "safe" is 1


class GuardUnavailableError(RuntimeError):
    """Raised when the guard model is unreachable, times out, or returns a 5xx error."""


class GuardBlockedError(RuntimeError):
    """Raised when the guard classifies input as unsafe."""

    def __init__(self, category: str | None, raw_response: str) -> None:
        self.category = category
        self.raw_response = raw_response
        super().__init__(f"Input blocked by guard: {category}")


@dataclass
class GuardVerdict:
    safe: bool
    category: str | None = None
    raw_response: str = field(default="")


class LlamaGuardClient:
    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or os.environ.get("LLM_API_KEY", "placeholder")
        self._client = OpenAI(
            base_url=_LLM_BASE_URL,
            api_key=key,
            timeout=_TIMEOUT,
            max_retries=0,
        )

    def classify_input(self, text: str) -> GuardVerdict:
        """Classify user input. Returns GuardVerdict or raises GuardBlockedError.

        Raises GuardUnavailableError on network/server errors (fail-closed).
        """
        try:
            response = self._client.chat.completions.create(
                model=_GUARD_MODEL,
                messages=[{"role": "user", "content": text}],
                max_tokens=_MAX_TOKENS,
                temperature=0,
            )
        except (APITimeoutError, APIConnectionError) as exc:
            raise GuardUnavailableError(f"Guard unreachable: {exc}") from exc
        except APIStatusError as exc:
            if exc.status_code >= 500:
                raise GuardUnavailableError(f"Guard server error {exc.status_code}: {exc}") from exc
            raise

        raw = (response.choices[0].message.content or "").strip()
        is_safe = not raw.lower().startswith("unsafe")
        if not is_safe:
            # raw is "unsafe\nS4" — extract the category code after the newline
            parts = raw.split("\n", 1)
            category = parts[1].strip() if len(parts) > 1 else "unknown"
        else:
            category = None
        return GuardVerdict(safe=is_safe, category=category, raw_response=raw)
