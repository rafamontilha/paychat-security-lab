"""Unit tests for the 5 Variant A tools.

Tests run against a real Postgres + in-memory Chroma. No ANTHROPIC_API_KEY needed.
Requires: uv sync --extra rag --group dev
"""

import os

import chromadb
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.agents.tools.get_order import make_get_order_tool
from app.infrastructure.agents.tools.get_user_info import make_get_user_info_tool
from app.infrastructure.agents.tools.process_refund import make_process_refund_tool
from app.infrastructure.agents.tools.search_products import make_search_products_tool
from app.infrastructure.agents.tools.send_message import make_send_message_tool
from app.infrastructure.persistence.models import Base, Order, Role, User
from app.infrastructure.rag.ingest import ingest_products

# ---------------------------------------------------------------------------
# Session-scoped fixtures
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
def chroma(db_session) -> chromadb.ClientAPI:
    client = chromadb.EphemeralClient()
    ingest_products(client, db_session)
    return client


@pytest.fixture(scope="module")
def buyer(db_session) -> User:
    return db_session.query(User).filter(User.role == Role.buyer).first()


@pytest.fixture(scope="module")
def admin(db_session) -> User:
    return db_session.query(User).filter(User.role == Role.admin).first()


@pytest.fixture(scope="module")
def seller(db_session) -> User:
    return db_session.query(User).filter(User.role == Role.seller).first()


def _actor(user: User, session_token: str = "test-token") -> dict:
    return {
        "user_id": user.id,
        "role": user.role.value,
        "session_token": session_token,
        "name": user.name,
    }


# ---------------------------------------------------------------------------
# search_products
# ---------------------------------------------------------------------------


def test_search_products_returns_results(chroma, db_session) -> None:
    tool = make_search_products_tool(chroma)
    result = tool.invoke({"query": "tênis"})
    assert isinstance(result, str)
    assert "product_" in result


def test_search_products_has_expected_fields(chroma) -> None:
    tool = make_search_products_tool(chroma)
    result = tool.invoke({"query": "eletrônico"})
    assert "score=" in result
    assert "category=" in result


# ---------------------------------------------------------------------------
# get_order
# ---------------------------------------------------------------------------


def test_get_order_own_order(buyer, db_session) -> None:
    order = db_session.query(Order).filter(Order.buyer_id == buyer.id).first()
    if not order:
        pytest.skip("No order for this buyer")
    tool = make_get_order_tool(_actor(buyer), db_session)
    result = tool.invoke({"order_id": order.id})
    assert f"order_id={order.id}" in result
    assert "status=" in result


def test_get_order_other_buyers_order_denied(buyer, db_session) -> None:
    other_buyer = (
        db_session.query(User).filter(User.role == Role.buyer, User.id != buyer.id).first()
    )
    order = db_session.query(Order).filter(Order.buyer_id == other_buyer.id).first()
    if not order:
        pytest.skip("No order for other buyer")
    tool = make_get_order_tool(_actor(buyer), db_session)
    result = tool.invoke({"order_id": order.id})
    assert "Access denied" in result


def test_get_order_admin_can_see_any(admin, db_session) -> None:
    order = db_session.query(Order).first()
    tool = make_get_order_tool(_actor(admin), db_session)
    result = tool.invoke({"order_id": order.id})
    assert f"order_id={order.id}" in result


# ---------------------------------------------------------------------------
# process_refund
# ---------------------------------------------------------------------------


def test_process_refund_other_order_denied(buyer, db_session) -> None:
    other_buyer = (
        db_session.query(User).filter(User.role == Role.buyer, User.id != buyer.id).first()
    )
    order = db_session.query(Order).filter(Order.buyer_id == other_buyer.id).first()
    if not order:
        pytest.skip("No order for other buyer")
    tool = make_process_refund_tool(_actor(buyer), db_session)
    result = tool.invoke({"order_id": order.id})
    assert "Access denied" in result


def test_process_refund_own_order(buyer, db_session) -> None:
    from app.infrastructure.persistence.models import OrderStatus

    order = (
        db_session.query(Order)
        .filter(Order.buyer_id == buyer.id, Order.status != OrderStatus.refunded)
        .first()
    )
    if not order:
        pytest.skip("No refundable order for this buyer")
    tool = make_process_refund_tool(_actor(buyer), db_session)
    result = tool.invoke({"order_id": order.id})
    assert "Refund initiated" in result or "already refunded" in result


# ---------------------------------------------------------------------------
# send_message
# ---------------------------------------------------------------------------


def test_send_message_persists_with_correct_sender(buyer, seller, db_session) -> None:
    from app.infrastructure.persistence.models import Message

    tool = make_send_message_tool(_actor(buyer), db_session)
    result = tool.invoke({"recipient_id": seller.id, "content": "Teste de mensagem."})
    assert "sent to" in result

    db_session.expire_all()
    msg = (
        db_session.query(Message)
        .filter(Message.sender_id == buyer.id, Message.recipient_id == seller.id)
        .order_by(Message.id.desc())
        .first()
    )
    assert msg is not None
    assert msg.sender_id == buyer.id


# ---------------------------------------------------------------------------
# get_user_info
# ---------------------------------------------------------------------------


def test_get_user_info_denied_for_buyer(buyer, db_session) -> None:
    tool = make_get_user_info_tool(_actor(buyer), db_session)
    result = tool.invoke({"user_id": buyer.id})
    assert "Access denied" in result


def test_get_user_info_allowed_for_admin(admin, buyer, db_session) -> None:
    tool = make_get_user_info_tool(_actor(admin), db_session)
    result = tool.invoke({"user_id": buyer.id})
    assert f"user_id={buyer.id}" in result
    assert "email=" in result
