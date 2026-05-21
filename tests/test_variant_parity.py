"""Variant parity tests — require both ANTHROPIC_API_KEY and GROQ_API_KEY.

Excluded from CI by default (marker: integration).
Run locally: pytest tests/test_variant_parity.py -m integration -v

For each of the 10 prompts below, both Variant A (Claude) and Variant B (Llama)
must invoke the same primary tool (first tool_call in the trace).

Done-when criterion from roadmap: "meu último pedido" produces an equivalent
get_order tool call in both variants returning the same order_id from the DB.
"""

import os

import chromadb
import pytest
import redis as redis_lib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.domain.entities.agent_trace import TraceStep
from app.infrastructure.persistence.models import Base, Order, Role, User

# ---------------------------------------------------------------------------
# 10 parity prompts — 2 per tool, covering all 5 tools
# ---------------------------------------------------------------------------

PARITY_PROMPTS: list[tuple[str, str]] = [
    # (message, expected_first_tool)
    ("buscar tênis preto", "search_products"),
    ("quero encontrar uma bolsa de couro", "search_products"),
    ("meu último pedido", "get_order"),
    ("qual o status do pedido mais recente?", "get_order"),
    ("quero reembolso do pedido 1", "process_refund"),
    ("preciso cancelar o pedido 1", "process_refund"),
    ("manda mensagem para o usuário 2 dizendo olá", "send_message"),
    ("envia aviso ao vendedor do pedido 1", "send_message"),
    ("informações do usuário 1", "get_user_info"),
    ("dados do perfil do usuário 2", "get_user_info"),
]

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
def admin_user(db_session) -> User:
    return db_session.query(User).filter(User.role == Role.admin).first()


@pytest.fixture(scope="module")
def admin_actor(admin_user: User) -> dict:
    return {
        "user_id": admin_user.id,
        "role": admin_user.role.value,
        "session_token": "parity-test-token",
        "name": admin_user.name,
    }


@pytest.fixture(scope="module")
def chroma_client(db_session):
    from app.infrastructure.rag.ingest import ingest_faq, ingest_products

    client = chromadb.EphemeralClient()
    ingest_products(client, db_session)
    ingest_faq(client)
    return client


@pytest.fixture(scope="module")
def redis_client():
    return redis_lib.from_url(
        os.environ.get("REDIS_URL", "redis://localhost:6379"), decode_responses=True
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _first_tool_name(trace: list[TraceStep]) -> str | None:
    for step in trace:
        if step.type == "tool_call":
            return step.tool_name
    return None


def _run_variant_a(message: str, actor: dict, db, chroma, redis) -> list[TraceStep]:
    from app.infrastructure.agents.variant_a_claude import VariantAClaude

    agent = VariantAClaude(
        actor_context={**actor, "session_token": f"parity-a-{hash(message)}"},
        db=db,
        chroma=chroma,
        redis_client=redis,
    )
    _, trace = agent.run(message)
    return trace


def _run_variant_b(message: str, actor: dict, db, chroma, redis) -> list[TraceStep]:
    from app.infrastructure.agents.variant_b_llama import VariantBLlama

    agent = VariantBLlama(
        actor_context={**actor, "session_token": f"parity-b-{hash(message)}"},
        db=db,
        chroma=chroma,
        redis_client=redis,
    )
    _, trace = agent.run(message)
    return trace


# ---------------------------------------------------------------------------
# Parity tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize("message,expected_tool", PARITY_PROMPTS)
def test_variant_parity(
    message: str,
    expected_tool: str,
    admin_actor,
    db_session,
    chroma_client,
    redis_client,
) -> None:
    """Both A and B must call the same primary tool for each benign prompt."""
    trace_a = _run_variant_a(message, admin_actor, db_session, chroma_client, redis_client)
    trace_b = _run_variant_b(message, admin_actor, db_session, chroma_client, redis_client)

    tool_a = _first_tool_name(trace_a)
    tool_b = _first_tool_name(trace_b)

    assert tool_a == tool_b, (
        f"Prompt: {message!r}\n"
        f"  Variant A first tool: {tool_a}\n"
        f"  Variant B first tool: {tool_b}\n"
        "Both variants must call the same primary tool for parity."
    )


@pytest.mark.integration
def test_canonical_get_order_returns_same_record(
    admin_actor, db_session, chroma_client, redis_client
) -> None:
    """'meu último pedido' — both variants return the same order_id in tool_result."""
    message = "meu último pedido"

    trace_a = _run_variant_a(message, admin_actor, db_session, chroma_client, redis_client)
    trace_b = _run_variant_b(message, admin_actor, db_session, chroma_client, redis_client)

    def _get_order_result(trace: list[TraceStep]) -> str | None:
        for step in trace:
            if step.type == "tool_return" and step.tool_name == "get_order":
                return step.tool_result
        return None

    result_a = _get_order_result(trace_a)
    result_b = _get_order_result(trace_b)

    assert result_a is not None, "Variant A did not call get_order"
    assert result_b is not None, "Variant B did not call get_order"

    # Both should reference the same order — extract order_id from result string
    def _order_id(result: str) -> str | None:
        for part in result.split():
            if part.startswith("order_id="):
                return part
        return None

    assert _order_id(result_a) == _order_id(result_b), (
        f"order_id mismatch:\n  A: {result_a}\n  B: {result_b}"
    )
