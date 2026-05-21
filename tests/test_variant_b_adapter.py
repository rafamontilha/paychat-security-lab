"""Tests for the Variant B adapter contract.

Group A (no DATABASE_URL needed — graph is mocked after construction):
  - Protocol compliance
  - max_iterations_reached
  - TraceStep schema
  - Redis history TTL/key
  - TraceStep round-trip serialisation

Group B (requires DATABASE_URL + seed data):
  - actor_context immutability via real tool + real DB
"""

import os
from unittest.mock import MagicMock

import chromadb
import pytest
import redis as redis_lib
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.errors import GraphRecursionError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.domain.entities.agent_trace import TraceStep
from app.domain.ports.agent_runtime import AgentRuntime
from app.infrastructure.persistence.models import Base, Order, Role, User

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _fake_actor(session_token: str = "test-b") -> dict:
    return {"user_id": 1, "role": "buyer", "session_token": session_token, "name": "Test"}


def _mock_redis() -> MagicMock:
    r = MagicMock(spec=redis_lib.Redis)
    r.get.return_value = None
    return r


def _make_agent(session_token: str = "test-b"):
    """Construct VariantBLlama with placeholder API key (no real LLM calls)."""
    from app.infrastructure.agents.variant_b_llama import VariantBLlama

    return VariantBLlama(
        actor_context=_fake_actor(session_token),
        db=MagicMock(),
        chroma=chromadb.EphemeralClient(),
        redis_client=_mock_redis(),
    )


def _graph_returns(final_text: str, history_len: int = 1) -> MagicMock:
    """Graph mock that returns a single AIMessage after history_len messages."""
    human = HumanMessage(content="query")
    final = AIMessage(content=final_text)
    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {"messages": [human] * history_len + [final]}
    return mock_graph


# ---------------------------------------------------------------------------
# Group A — no DATABASE_URL needed
# ---------------------------------------------------------------------------


def test_variant_b_implements_agent_runtime_protocol() -> None:
    agent = _make_agent()
    assert isinstance(agent, AgentRuntime)


def test_trace_step_schema_has_required_fields() -> None:
    """TraceStep fields are exactly what Fase 7 harness expects — no additions or removals."""
    expected = {"type", "content", "tool_name", "tool_args", "tool_result", "timestamp"}
    actual = set(TraceStep.model_fields.keys())
    assert expected == actual, (
        f"TraceStep schema changed. "
        f"Missing: {expected - actual}, Extra: {actual - expected}"
    )


def test_max_iterations_returns_structured_response() -> None:
    """recursion_limit exceeded → 'max_iterations_reached', not an exception."""
    agent = _make_agent("iter-test-b")
    agent._graph = MagicMock()
    agent._graph.invoke.side_effect = GraphRecursionError()

    response, trace = agent.run("keep calling get_order forever")

    assert response == "max_iterations_reached"
    assert len(trace) >= 1
    assert trace[-1].type == "final"
    assert trace[-1].content == "max_iterations_reached"


def test_trace_step_serialises_and_deserialises() -> None:
    """A trace produced by Variant B round-trips through TraceStep schema."""
    agent = _make_agent("schema-test-b")
    agent._graph = _graph_returns("Aqui está o resultado.")

    _, trace = agent.run("olá")

    for step in trace:
        dumped = step.model_dump()
        restored = TraceStep.model_validate(dumped)
        assert restored.type == step.type
        assert restored.content == step.content


def test_history_saved_to_redis_with_correct_key_and_ttl() -> None:
    from app.infrastructure.agents.variant_b_llama import VariantBLlama

    redis_mock = _mock_redis()
    agent = VariantBLlama(
        actor_context=_fake_actor("history-test-b"),
        db=MagicMock(),
        chroma=chromadb.EphemeralClient(),
        redis_client=redis_mock,
    )
    agent._graph = _graph_returns("ok")
    agent.run("olá")

    redis_mock.setex.assert_called_once()
    key_arg = redis_mock.setex.call_args[0][0]
    ttl_arg = redis_mock.setex.call_args[0][1]
    assert "history-test-b" in key_arg
    assert ttl_arg == 3600


# ---------------------------------------------------------------------------
# Group B — requires DATABASE_URL + seed data
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


@pytest.fixture(scope="module")
def seed_db(db_session):
    from scripts.seed import seed

    seed(db_session)


@pytest.fixture(scope="module")
def buyer(db_session, seed_db) -> User:
    return db_session.query(User).filter(User.role == Role.buyer).first()


def test_get_order_uses_closure_context_not_message_id(buyer, db_session) -> None:
    """Tool always uses actor_context from closure — model cannot inject a different user_id."""
    from app.infrastructure.agents.tools.get_order import make_get_order_tool

    other_buyer = (
        db_session.query(User).filter(User.role == Role.buyer, User.id != buyer.id).first()
    )
    other_order = db_session.query(Order).filter(Order.buyer_id == other_buyer.id).first()
    if not other_order:
        pytest.skip("No order for other buyer")

    actor = {"user_id": buyer.id, "role": buyer.role.value, "session_token": "t", "name": "T"}
    tool = make_get_order_tool(actor, db_session)
    result = tool.invoke({"order_id": other_order.id})
    assert "Access denied" in result


def test_get_user_info_role_comes_from_closure_not_message(buyer, db_session) -> None:
    """Role in actor_context cannot be elevated by model passing a different value."""
    from app.infrastructure.agents.tools.get_user_info import make_get_user_info_tool

    actor = {"user_id": buyer.id, "role": buyer.role.value, "session_token": "t", "name": "T"}
    tool = make_get_user_info_tool(actor, db_session)
    result = tool.invoke({"user_id": buyer.id})
    assert "Access denied" in result
