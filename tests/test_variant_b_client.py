"""Tests for Variant B Groq client configuration and retry logic.

No GROQ_API_KEY needed — all LLM calls are mocked.
"""

from unittest.mock import MagicMock, call, patch

import chromadb
import pytest
import redis as redis_lib
from openai import RateLimitError

from app.infrastructure.agents.variant_b_llama import (
    _GROQ_BASE_URL,
    _MODEL,
    _RETRY_DELAYS,
    _invoke_with_retry,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_rate_limit_error() -> RateLimitError:
    response = MagicMock()
    response.status_code = 429
    response.headers = {}
    return RateLimitError("Rate limit exceeded", response=response, body=None)


def _fake_actor(session_token: str = "t") -> dict:
    return {"user_id": 1, "role": "buyer", "session_token": session_token, "name": "T"}


# ---------------------------------------------------------------------------
# Client configuration
# ---------------------------------------------------------------------------


def test_groq_base_url_constant() -> None:
    assert _GROQ_BASE_URL == "https://api.groq.com/openai/v1"


def test_groq_model_constant() -> None:
    assert "llama" in _MODEL.lower()


def test_client_instantiated_with_correct_params() -> None:
    fake_db = MagicMock()
    fake_redis = MagicMock(spec=redis_lib.Redis)
    fake_redis.get.return_value = None
    fake_chroma = chromadb.EphemeralClient()

    with patch("app.infrastructure.agents.variant_b_llama.ChatOpenAI") as MockLLM:
        mock_instance = MagicMock()
        mock_instance.bind_tools.return_value = mock_instance
        MockLLM.return_value = mock_instance

        from app.infrastructure.agents.variant_b_llama import VariantBLlama

        VariantBLlama(
            actor_context=_fake_actor(),
            db=fake_db,
            chroma=fake_chroma,
            redis_client=fake_redis,
        )

        kwargs = MockLLM.call_args.kwargs
        assert kwargs["base_url"] == _GROQ_BASE_URL
        assert kwargs["model"] == _MODEL
        assert kwargs["max_retries"] == 0


def test_import_succeeds_without_groq_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    # Import must succeed; key is resolved lazily at instantiation
    from app.infrastructure.agents import variant_b_llama  # noqa: F401


# ---------------------------------------------------------------------------
# _invoke_with_retry
# ---------------------------------------------------------------------------


def test_invoke_with_retry_succeeds_first_attempt() -> None:
    graph = MagicMock()
    graph.invoke.return_value = {"messages": []}

    result = _invoke_with_retry(graph, {}, {})

    assert result == {"messages": []}
    assert graph.invoke.call_count == 1


def test_invoke_with_retry_retries_on_429_and_succeeds() -> None:
    graph = MagicMock()
    err = _make_rate_limit_error()
    graph.invoke.side_effect = [err, err, {"messages": []}]

    with patch("app.infrastructure.agents.variant_b_llama._SLEEP") as mock_sleep:
        result = _invoke_with_retry(graph, {}, {})

    assert result == {"messages": []}
    assert graph.invoke.call_count == 3
    assert mock_sleep.call_count == 2
    assert mock_sleep.call_args_list == [call(_RETRY_DELAYS[0]), call(_RETRY_DELAYS[1])]


def test_invoke_with_retry_raises_after_all_retries_exhausted() -> None:
    graph = MagicMock()
    err = _make_rate_limit_error()
    graph.invoke.side_effect = err  # always raises

    with patch("app.infrastructure.agents.variant_b_llama._SLEEP"):
        with pytest.raises(RateLimitError):
            _invoke_with_retry(graph, {}, {})

    assert graph.invoke.call_count == len(_RETRY_DELAYS) + 1


def test_invoke_with_retry_does_not_swallow_non_429_errors() -> None:
    graph = MagicMock()
    graph.invoke.side_effect = ValueError("unexpected error")

    with pytest.raises(ValueError, match="unexpected error"):
        _invoke_with_retry(graph, {}, {})

    assert graph.invoke.call_count == 1
