"""Anti-theft layer: per-session rate limiting + query-budget probing detection.

Two Redis-backed controls applied before the agent runs (when defenses are enabled):

1. Rate limit — at most ``max_requests`` agent calls per session token per ``window_seconds``
   (default 60/hour). Fixed-window counter via INCR + EXPIRE; the 61st call is rejected.

2. Query budget — model-extraction attacks fire many near-identical queries in a short burst.
   We keep a short rolling history of normalized queries per session; when too many
   near-duplicates appear, a progressively longer cooldown blocks the session.

The Redis client is injected (decode_responses=True expected, so values come back as str).
"""

import re

MAX_REQUESTS_PER_WINDOW = 60
WINDOW_SECONDS = 3600
PROBING_HISTORY = 10
PROBING_SIMILARITY = 0.8
PROBING_THRESHOLD = 5
COOLDOWN_BASE_SECONDS = 60

_WORD_RE = re.compile(r"\w+", re.UNICODE)


def _tokens(text: str) -> frozenset[str]:
    return frozenset(_WORD_RE.findall(text.lower()))


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


class AntiTheftGuard:
    def __init__(
        self,
        redis_client,
        *,
        max_requests: int = MAX_REQUESTS_PER_WINDOW,
        window_seconds: int = WINDOW_SECONDS,
        probing_threshold: int = PROBING_THRESHOLD,
    ) -> None:
        self._redis = redis_client
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._probing_threshold = probing_threshold

    def check_rate_limit(self, session_token: str) -> tuple[bool, str]:
        key = f"antitheft:rate:{session_token}"
        count = int(self._redis.incr(key))
        if count == 1:
            self._redis.expire(key, self._window_seconds)
        if count > self._max_requests:
            return False, f"rate_limit_exceeded:{count}/{self._max_requests}"
        return True, f"rate_ok:{count}"

    def check_query_budget(self, session_token: str, query: str) -> tuple[bool, str]:
        cooldown_key = f"antitheft:cooldown:{session_token}"
        if self._redis.get(cooldown_key):
            return False, "probing_cooldown_active"

        history_key = f"antitheft:qhist:{session_token}"
        current = _tokens(query)
        recent = self._redis.lrange(history_key, 0, PROBING_HISTORY - 1) or []
        similar = sum(1 for r in recent if _jaccard(current, _tokens(r)) >= PROBING_SIMILARITY)

        self._redis.lpush(history_key, query)
        self._redis.ltrim(history_key, 0, PROBING_HISTORY - 1)
        self._redis.expire(history_key, self._window_seconds)

        if similar >= self._probing_threshold:
            level = int(self._redis.incr(f"antitheft:cdlevel:{session_token}"))
            duration = COOLDOWN_BASE_SECONDS * (2 ** (level - 1))
            self._redis.setex(cooldown_key, duration, "1")
            return False, f"probing_detected:cooldown={duration}s"
        return True, f"qbudget_ok:{similar}_similar"

    def check(self, session_token: str, query: str) -> tuple[bool, str]:
        """Run rate limit then query-budget. Returns (allowed, reason); first block wins."""
        allowed, reason = self.check_rate_limit(session_token)
        if not allowed:
            return False, reason
        return self.check_query_budget(session_token, query)
