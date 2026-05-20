"""Tests for Variant A agent contract — no ANTHROPIC_API_KEY needed.

Covers:
- actor_context immutability (model cannot change user_id via message)
- recursion_limit=10 returns max_iterations_reached (not an exception)

Integration tests that call the real Claude API are marked @pytest.mark.integration
and excluded from the CI default run.
"""

import os
from unittest.mock import MagicMock, patch

import chromadb
import pytest
from langchain_core.messages import AIMessage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.agents.tools.get_order import make_get_order_tool
from app.infrastructure.agents.tools.get_user_info import make_get_user_info_tool
from app.infrastructure.persistence.models import Base, Order, Role, User

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def db_engine():
    url = os.environ["DATABASE_URL"]
    engine = create_engine(url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="module", autouse=True)
def seed_db(db_session):
    from scripts.seed import seed

    seed(db_session)


@pytest.fixture(scope="module")
def buyer(db_session) -> User:
    return db_session.query(User).filter(User.role == Role.buyer).first()


def _actor(user: User, session_token: str = "test-token") -> dict:
    return {
        "user_id": user.id,
        "role": user.role.value,
        "session_token": session_token,
        "name": user.name,
    }


# ---------------------------------------------------------------------------
# actor_context immutability
# ---------------------------------------------------------------------------


def test_get_order_uses_closure_context_not_message_id(buyer, db_session) -> None:
    """Tool always uses actor_context from closure — model cannot inject a different user_id."""
    other_buyer = (
        db_session.query(User).filter(User.role == Role.buyer, User.id != buyer.id).first()
    )
    other_order = db_session.query(Order).filter(Order.buyer_id == other_buyer.id).first()
    if not other_order:
        pytest.skip("No order for other buyer")

    # Tool is built with buyer's actor_context
    tool = make_get_order_tool(_actor(buyer), db_session)

    # Even if the model passes other_buyer's order_id, the RBAC check uses buyer's actor_context
    result = tool.invoke({"order_id": other_order.id})
    assert (
        "Access denied" in result
    ), "Tool should deny access using closure actor_context, not trust model-supplied user_id"


def test_get_user_info_role_comes_from_closure_not_message(buyer, db_session) -> None:
    """Role in actor_context cannot be elevated by model passing a different value."""
    tool = make_get_user_info_tool(_actor(buyer), db_session)

    # Simulate model trying to call get_user_info — role check uses closure
    result = tool.invoke({"user_id": buyer.id})
    assert (
        "Access denied" in result
    ), "get_user_info must use role from closure actor_context, not from model arguments"


# ---------------------------------------------------------------------------
# Iteration limit
# ---------------------------------------------------------------------------


def test_max_iterations_returns_structured_response(buyer, db_session) -> None:
    """When recursion_limit is exceeded, agent returns 'max_iterations_reached'.

    Must not raise an exception — returns the sentinel string instead.
    """
    import redis as redis_lib

    from app.infrastructure.agents.variant_a_claude import VariantAClaude

    chroma = chromadb.EphemeralClient()
    redis_mock = MagicMock(spec=redis_lib.Redis)
    redis_mock.get.return_value = None  # empty history

    actor = _actor(buyer, session_token="iter-test-token")

    # Mock ChatAnthropic so every call returns a tool_call (forces infinite loop)
    fake_tool_call = AIMessage(
        content="",
        tool_calls=[
            {"name": "get_order", "args": {"order_id": 1}, "id": "tc_1", "type": "tool_call"}
        ],
    )

    with patch("app.infrastructure.agents.variant_a_claude.ChatAnthropic") as MockLLM:
        mock_llm_instance = MagicMock()
        mock_llm_instance.bind_tools.return_value = mock_llm_instance
        mock_llm_instance.invoke.return_value = fake_tool_call
        MockLLM.return_value = mock_llm_instance

        agent = VariantAClaude(
            actor_context=actor,
            db=db_session,
            chroma=chroma,
            redis_client=redis_mock,
        )
        response, trace = agent.run("keep calling get_order forever")

    assert response == "max_iterations_reached"
    assert len(trace) >= 1
    assert trace[-1].type == "final"
    assert trace[-1].content == "max_iterations_reached"


# ---------------------------------------------------------------------------
# Integration tests (require ANTHROPIC_API_KEY — excluded from CI default)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_agent_search_products_real(buyer, db_session) -> None:
    """Real call to Claude — search_products tool is invoked in the ReAct trace."""
    import redis as redis_lib

    from app.infrastructure.agents.variant_a_claude import VariantAClaude
    from app.infrastructure.rag.ingest import ingest_faq, ingest_products

    chroma = chromadb.EphemeralClient()
    ingest_products(chroma, db_session)
    ingest_faq(chroma)

    redis_client = redis_lib.from_url(
        os.environ.get("REDIS_URL", "redis://localhost:6379"), decode_responses=True
    )
    actor = _actor(buyer, session_token="integration-test")
    agent = VariantAClaude(
        actor_context=actor, db=db_session, chroma=chroma, redis_client=redis_client
    )
    response, trace = agent.run("buscar tênis")

    tool_calls = [s for s in trace if s.type == "tool_call"]
    assert any(
        s.tool_name == "search_products" for s in tool_calls
    ), f"Expected search_products in trace, got: {[s.tool_name for s in tool_calls]}"
    assert response  # non-empty final response


@pytest.mark.integration
def test_agent_refund_denied_cross_actor(buyer, db_session) -> None:
    """Real call — process_refund on another user's order must be denied in trace."""
    import redis as redis_lib

    from app.infrastructure.agents.variant_a_claude import VariantAClaude
    from app.infrastructure.rag.ingest import ingest_products

    other_buyer = (
        db_session.query(User).filter(User.role == Role.buyer, User.id != buyer.id).first()
    )
    order = db_session.query(Order).filter(Order.buyer_id == other_buyer.id).first()
    if not order:
        pytest.skip("No order for other buyer")

    chroma = chromadb.EphemeralClient()
    ingest_products(chroma, db_session)
    redis_client = redis_lib.from_url(
        os.environ.get("REDIS_URL", "redis://localhost:6379"), decode_responses=True
    )
    actor = _actor(buyer, session_token="integration-refund-test")
    agent = VariantAClaude(
        actor_context=actor, db=db_session, chroma=chroma, redis_client=redis_client
    )
    response, trace = agent.run(f"quero reembolso do pedido {order.id}")

    tool_returns = [s for s in trace if s.type == "tool_return"]
    denied = any("Access denied" in (s.tool_result or "") for s in tool_returns)
    results = [s.tool_result for s in tool_returns]
    assert denied, f"Expected Access denied in tool returns, got: {results}"
