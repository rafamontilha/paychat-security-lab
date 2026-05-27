"""Rebuff-style prompt-injection defense: known-pattern heuristics + canary tokens.

Two complementary mechanisms:

1. Heuristic input check — matches the user input against known injection phrasings
   ("ignore previous instructions", "developer mode", attempts to close/forge the
   <USER_INPUT> delimiters, requests to reveal the system prompt, etc.). Cheap, runs
   before the model. Catches the most common direct-injection openers.

2. Canary token — a random secret injected into the system prompt. The model is told
   never to reveal it. If the token shows up in the output, the system prompt leaked
   (or the model was coerced into echoing its instructions) → the response is blocked.
"""

import re
import secrets

_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"ignore\s+(all\s+|any\s+)?(the\s+)?(previous|prior|above|earlier)\s+", re.I),
    re.compile(
        r"disregard\s+(all\s+|any\s+)?(the\s+)?(previous|prior|above|instructions|rules)", re.I
    ),
    re.compile(r"forget\s+(everything|all|your|the)\s+", re.I),
    re.compile(r"developer\s+mode", re.I),
    re.compile(r"\bDAN\b", re.I),
    re.compile(r"do\s+anything\s+now", re.I),
    re.compile(
        r"(reveal|show|print|repeat|dump|output)\b.{0,40}"
        r"(system\s+prompt|your\s+instructions|initial\s+prompt)",
        re.I,
    ),
    re.compile(r"you\s+are\s+now\s+(a|an|the)\b", re.I),
    re.compile(r"</?(system|user_input|instructions|assistant)\s*>", re.I),
    re.compile(r"new\s+(system\s+)?(instructions?|rules?|prompt)\s*:", re.I),
    re.compile(r"act\s+as\s+(if\s+)?(a|an|though)\b", re.I),
)


def make_canary() -> str:
    """Generate a unique canary token to embed in the system prompt."""
    return f"CANARY-{secrets.token_hex(8)}"


class RebuffDetector:
    def __init__(self, patterns: tuple[re.Pattern[str], ...] | None = None) -> None:
        self._patterns = patterns if patterns is not None else _INJECTION_PATTERNS

    def check_input(self, text: str) -> tuple[bool, str]:
        """Return (allowed, reason). allowed=False blocks on a known injection pattern."""
        for pattern in self._patterns:
            if pattern.search(text):
                return False, f"rebuff_heuristic:{pattern.pattern[:48]}"
        return True, "rebuff_ok"

    @staticmethod
    def detect_leak(output: str, canary: str) -> bool:
        """True if the canary token appears in the model output (prompt leak)."""
        return bool(canary) and canary in output
