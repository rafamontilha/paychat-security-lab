"""Variant parity tests — require both ANTHROPIC_API_KEY and GROQ_API_KEY.

Excluded from CI by default (marker: integration).
Run locally: pytest tests/test_variant_parity.py -m integration -v

For each of the 10 prompts below, both Variant A (Claude) and Variant B (Llama)
must invoke the expected tool somewhere in the trace.

Done-when criterion from roadmap: "meu último pedido" produces an equivalent
get_order tool call in both variants returning the same order_id from the DB.

Notes on assertion design
--------------------------
The assertion checks that the expected tool appears ANYWHERE in the trace (not
necessarily as the first call). This accommodates legitimate reasoning differences
between models: Claude tends to verify state before acting (e.g. get_order before
process_refund), while Llama may act directly. Both are correct; the parity property
is that both eventually invoke the right tool.

The get_user_info prompts use admin_actor because that tool is restricted to
admin/support roles — Claude correctly skips it for buyer actors while Llama
calls it and receives "Access denied", which would be a false parity failure.
"""

import os
import time

import chromadb
import pytest
import redis as redis_lib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.domain.entities.agent_trace import TraceStep
from app.infrastructure.persistence.models import Base, Role, User

# ---------------------------------------------------------------------------
# 10 parity prompts — 2 per tool, covering all 5 tools
# (message, expected_tool, actor_type)
# ---------------------------------------------------------------------------

PARITY_PROMPTS: list[tuple[str, str, str]] = [
    ("pesquisar tênis preto no catálogo", "search_products", "buyer"),
    ("quero encontrar uma bolsa de couro", "search_products", "buyer"),
    ("meu último pedido", "get_order", "buyer"),
    ("qual o status do pedido mais recente?", "get_order", "buyer"),
    ("quero reembolso do pedido 1", "process_refund", "buyer"),
    ("preciso cancelar o pedido 1", "process_refund", "buyer"),
    ("manda mensagem para o usuário 2 dizendo olá", "send_message", "buyer"),
    ("envia aviso ao vendedor do pedido 1", "send_message", "buyer"),
    ("informações do usuário 1", "get_user_info", "admin"),
    ("dados do perfil do usuário 2", "get_user_info", "admin"),
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
def buyer_user(db_session) -> User:
    return db_session.query(User).filter(User.role == Role.buyer).first()


@pytest.fixture(scope="module")
def buyer_actor(buyer_user: User) -> dict:
    return {
        "user_id": buyer_user.id,
        "role": buyer_user.role.value,
        "session_token": "parity-buyer-token",
        "name": buyer_user.name,
    }


@pytest.fixture(scope="module")
def admin_user(db_session) -> User:
    return db_session.query(User).filter(User.role == Role.admin).first()


@pytest.fixture(scope="module")
def admin_actor(admin_user: User) -> dict:
    return {
        "user_id": admin_user.id,
        "role": admin_user.role.value,
        "session_token": "parity-admin-token",
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


def _tool_used(trace: list[TraceStep], tool_name: str) -> bool:
    """Return True if tool_name appears anywhere in the trace as a tool_call."""
    return any(step.type == "tool_call" and step.tool_name == tool_name for step in trace)


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
@pytest.mark.parametrize("message,expected_tool,actor_type", PARITY_PROMPTS)
def test_variant_parity(
    message: str,
    expected_tool: str,
    actor_type: str,
    buyer_actor,
    admin_actor,
    db_session,
    chroma_client,
    redis_client,
) -> None:
    """Both A and B must invoke the expected tool somewhere in their traces."""
    # Throttle: Groq free tier ~6 000 TPM; pause prevents cascading 429s.
    time.sleep(30)
    actor = buyer_actor if actor_type == "buyer" else admin_actor
    trace_a = _run_variant_a(message, actor, db_session, chroma_client, redis_client)
    trace_b = _run_variant_b(message, actor, db_session, chroma_client, redis_client)

    used_a = _tool_used(trace_a, expected_tool)
    used_b = _tool_used(trace_b, expected_tool)

    assert used_a, (
        f"Prompt: {message!r}\n"
        f"  Variant A never called '{expected_tool}'. "
        f"Tools called: {[s.tool_name for s in trace_a if s.type == 'tool_call']}"
    )
    assert used_b, (
        f"Prompt: {message!r}\n"
        f"  Variant B never called '{expected_tool}'. "
        f"Tools called: {[s.tool_name for s in trace_b if s.type == 'tool_call']}"
    )


@pytest.mark.integration
def test_canonical_get_order_returns_same_record(
    buyer_actor, db_session, chroma_client, redis_client
) -> None:
    """'meu último pedido' — both variants return the same order_id in tool_result."""
    time.sleep(30)
    message = "meu último pedido"

    trace_a = _run_variant_a(message, buyer_actor, db_session, chroma_client, redis_client)
    trace_b = _run_variant_b(message, buyer_actor, db_session, chroma_client, redis_client)

    def _get_order_result(trace: list[TraceStep]) -> str | None:
        for step in trace:
            if step.type == "tool_return" and step.tool_name == "get_order":
                return step.tool_result
        return None

    result_a = _get_order_result(trace_a)
    result_b = _get_order_result(trace_b)

    assert result_a is not None, "Variant A did not call get_order"
    assert result_b is not None, "Variant B did not call get_order"

    def _order_id(result: str) -> str | None:
        for part in result.split():
            if part.startswith("order_id="):
                return part
        return None

    assert _order_id(result_a) == _order_id(result_b), (
        f"order_id mismatch:\n  A: {result_a}\n  B: {result_b}"
    )
