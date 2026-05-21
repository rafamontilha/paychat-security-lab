"""Tests for /api/agent/chat variant routing.

No ANTHROPIC_API_KEY or GROQ_API_KEY needed — agent classes are mocked.
Requires DATABASE_URL and REDIS_URL (same as smoke tests).
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.persistence.database import get_db
from app.infrastructure.rag.client import get_chroma_client
from app.infrastructure.web.fastapi_app import app

_MOCK_SESSION = MagicMock()
_MOCK_SESSION_FACTORY = MagicMock(return_value=_MOCK_SESSION)

_FAKE_ACTOR = {
    "user_id": 1,
    "role": "buyer",
    "session_token": "fake-token",
    "name": "Test User",
}

_CHAT_BODY = {"session_token": "fake-token", "message": "olá"}


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = lambda: MagicMock()
    app.dependency_overrides[get_chroma_client] = lambda: MagicMock()
    with patch(
        "app.infrastructure.web.middleware.audit_log.get_session_factory",
        return_value=_MOCK_SESSION_FACTORY,
    ):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c
    app.dependency_overrides.clear()


def _patch_redis():
    return patch(
        "app.infrastructure.web.routers.agent.get_redis",
        return_value=MagicMock(),
    )


def _patch_resolve_actor():
    return patch(
        "app.infrastructure.web.routers.agent._resolve_actor",
        return_value=_FAKE_ACTOR,
    )


def _mock_agent(response: str = "ok") -> MagicMock:
    agent = MagicMock()
    agent.run.return_value = (response, [])
    return agent


# ---------------------------------------------------------------------------
# Default variant (a)
# ---------------------------------------------------------------------------


def test_default_variant_dispatches_to_variant_a(client) -> None:
    mock_agent = _mock_agent()
    with (
        _patch_redis(),
        _patch_resolve_actor(),
        patch(
            "app.infrastructure.agents.variant_a_claude.VariantAClaude",
            return_value=mock_agent,
        ) as MockA,
    ):
        resp = client.post("/api/agent/chat", json=_CHAT_BODY)

    assert resp.status_code == 200
    MockA.assert_called_once()


# ---------------------------------------------------------------------------
# variant=b query parameter
# ---------------------------------------------------------------------------


def test_query_param_variant_b_dispatches_to_variant_b(client) -> None:
    mock_agent = _mock_agent()
    with (
        _patch_redis(),
        _patch_resolve_actor(),
        patch(
            "app.infrastructure.agents.variant_b_llama.VariantBLlama",
            return_value=mock_agent,
        ) as MockB,
    ):
        resp = client.post("/api/agent/chat?variant=b", json=_CHAT_BODY)

    assert resp.status_code == 200
    MockB.assert_called_once()


# ---------------------------------------------------------------------------
# X-Variant header
# ---------------------------------------------------------------------------


def test_header_x_variant_b_dispatches_to_variant_b(client) -> None:
    mock_agent = _mock_agent()
    with (
        _patch_redis(),
        _patch_resolve_actor(),
        patch(
            "app.infrastructure.agents.variant_b_llama.VariantBLlama",
            return_value=mock_agent,
        ) as MockB,
    ):
        resp = client.post(
            "/api/agent/chat",
            json=_CHAT_BODY,
            headers={"X-Variant": "b"},
        )

    assert resp.status_code == 200
    MockB.assert_called_once()


def test_header_overrides_query_param_when_both_present(client) -> None:
    """X-Variant header takes precedence over ?variant query param."""
    mock_agent = _mock_agent()
    with (
        _patch_redis(),
        _patch_resolve_actor(),
        patch(
            "app.infrastructure.agents.variant_b_llama.VariantBLlama",
            return_value=mock_agent,
        ) as MockB,
    ):
        resp = client.post(
            "/api/agent/chat?variant=a",
            json=_CHAT_BODY,
            headers={"X-Variant": "b"},
        )

    assert resp.status_code == 200
    MockB.assert_called_once()


# ---------------------------------------------------------------------------
# Invalid variant → 400
# ---------------------------------------------------------------------------


def test_invalid_variant_returns_400(client) -> None:
    with _patch_redis(), _patch_resolve_actor():
        resp = client.post("/api/agent/chat?variant=z", json=_CHAT_BODY)

    assert resp.status_code == 400
    assert "Unknown variant" in resp.json()["detail"]


def test_invalid_variant_via_header_returns_400(client) -> None:
    with _patch_redis(), _patch_resolve_actor():
        resp = client.post(
            "/api/agent/chat",
            json=_CHAT_BODY,
            headers={"X-Variant": "z"},
        )

    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Variant C routing
# ---------------------------------------------------------------------------


def test_query_param_variant_c_dispatches_to_variant_c(client) -> None:
    mock_agent = _mock_agent()
    with (
        _patch_redis(),
        _patch_resolve_actor(),
        patch(
            "app.infrastructure.agents.variant_c_pipeline.VariantCPipeline",
            return_value=mock_agent,
        ) as MockC,
    ):
        resp = client.post("/api/agent/chat?variant=c", json=_CHAT_BODY)

    assert resp.status_code == 200
    MockC.assert_called_once()


def test_header_x_variant_c_dispatches_to_variant_c(client) -> None:
    mock_agent = _mock_agent()
    with (
        _patch_redis(),
        _patch_resolve_actor(),
        patch(
            "app.infrastructure.agents.variant_c_pipeline.VariantCPipeline",
            return_value=mock_agent,
        ) as MockC,
    ):
        resp = client.post(
            "/api/agent/chat",
            json=_CHAT_BODY,
            headers={"X-Variant": "c"},
        )

    assert resp.status_code == 200
    MockC.assert_called_once()
