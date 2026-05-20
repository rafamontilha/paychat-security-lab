"""Smoke tests for the Fase 2 marketplace endpoints.

Requires DATABASE_URL and REDIS_URL env vars pointing to running services.
In CI these are provided by the docker-compose service_healthy checks.
"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models import Base, Role, User
from app.infrastructure.web.fastapi_app import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def db_engine():
    url = os.environ["DATABASE_URL"]
    engine = create_engine(url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="session", autouse=True)
def seed_db(db_session):
    """Run seed once per test session."""
    from scripts.seed import seed

    seed(db_session)


@pytest.fixture(scope="session")
def client(db_engine):
    Session = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)

    def override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def buyer_token(client, db_session):
    buyer = db_session.query(User).filter(User.role == Role.buyer).first()
    resp = client.post("/api/auth/login", json={"api_key": buyer.api_key})
    assert resp.status_code == 200
    return resp.json()["session_token"]


@pytest.fixture(scope="session")
def admin_token(client, db_session):
    admin = db_session.query(User).filter(User.role == Role.admin).first()
    resp = client.post("/api/auth/login", json={"api_key": admin.api_key})
    assert resp.status_code == 200
    return resp.json()["session_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def test_login_valid(client, db_session):
    user = db_session.query(User).filter(User.role == Role.buyer).first()
    resp = client.post("/api/auth/login", json={"api_key": user.api_key})
    assert resp.status_code == 200
    data = resp.json()
    assert "session_token" in data
    assert data["role"] == "buyer"


def test_login_invalid_key(client):
    resp = client.post("/api/auth/login", json={"api_key": "nonexistent"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------


def test_list_products(client, buyer_token):
    resp = client.get("/api/products", headers=auth(buyer_token))
    assert resp.status_code == 200
    assert len(resp.json()) > 0


def test_get_product(client, buyer_token, db_session):
    from app.infrastructure.persistence.models import Product

    p = db_session.query(Product).first()
    resp = client.get(f"/api/products/{p.id}", headers=auth(buyer_token))
    assert resp.status_code == 200
    assert resp.json()["id"] == p.id


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------


def test_list_orders_buyer_sees_own(client, buyer_token, db_session):
    from app.infrastructure.persistence.models import Order

    buyer = db_session.query(User).filter(User.role == Role.buyer).first()
    resp = client.get("/api/orders", headers=auth(buyer_token))
    assert resp.status_code == 200
    ids = {o["buyer_id"] for o in resp.json()}
    assert ids == {buyer.id}


def test_get_order_forbidden_for_other_buyer(client, db_session):
    from app.infrastructure.persistence.models import Order

    buyers = db_session.query(User).filter(User.role == Role.buyer).limit(2).all()
    assert len(buyers) >= 2
    buyer_a, buyer_b = buyers[0], buyers[1]

    # Login as buyer_b and try to access buyer_a's order
    resp_login = client.post("/api/auth/login", json={"api_key": buyer_b.api_key})
    token_b = resp_login.json()["session_token"]

    order_a = db_session.query(Order).filter(Order.buyer_id == buyer_a.id).first()
    if not order_a:
        pytest.skip("No order for buyer_a")

    resp = client.get(f"/api/orders/{order_a.id}", headers=auth(token_b))
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Users — RBAC
# ---------------------------------------------------------------------------


def test_get_user_forbidden_for_buyer(client, buyer_token, db_session):
    user = db_session.query(User).first()
    resp = client.get(f"/api/users/{user.id}", headers=auth(buyer_token))
    assert resp.status_code == 403


def test_get_user_allowed_for_admin(client, admin_token, db_session):
    user = db_session.query(User).first()
    resp = client.get(f"/api/users/{user.id}", headers=auth(admin_token))
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


def test_send_message(client, buyer_token, db_session):
    seller = db_session.query(User).filter(User.role == Role.seller).first()
    resp = client.post(
        "/api/messages",
        json={"recipient_id": seller.id, "content": "Olá, tenho uma dúvida."},
        headers=auth(buyer_token),
    )
    assert resp.status_code == 201
    assert resp.json()["recipient_id"] == seller.id


# ---------------------------------------------------------------------------
# Refunds
# ---------------------------------------------------------------------------


def test_refund_own_order(client, buyer_token, db_session):
    from app.infrastructure.persistence.models import Order, OrderStatus

    buyer = db_session.query(User).filter(User.role == Role.buyer).first()
    order = (
        db_session.query(Order)
        .filter(Order.buyer_id == buyer.id, Order.status != OrderStatus.refunded)
        .first()
    )
    if not order:
        pytest.skip("No refundable order for buyer")

    resp = client.post("/api/refunds", json={"order_id": order.id}, headers=auth(buyer_token))
    assert resp.status_code == 200
    assert resp.json()["status"] == "refunded"


def test_refund_other_users_order_forbidden(client, db_session):
    from app.infrastructure.persistence.models import Order

    buyers = db_session.query(User).filter(User.role == Role.buyer).limit(2).all()
    buyer_a, buyer_b = buyers[0], buyers[1]

    resp_login = client.post("/api/auth/login", json={"api_key": buyer_b.api_key})
    token_b = resp_login.json()["session_token"]

    order_a = db_session.query(Order).filter(Order.buyer_id == buyer_a.id).first()
    if not order_a:
        pytest.skip("No order for buyer_a")

    resp = client.post(
        "/api/refunds", json={"order_id": order_a.id}, headers=auth(token_b)
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------


def test_audit_log_records_requests(client, buyer_token, db_session):
    from app.infrastructure.persistence.models import AuditLog

    # Trigger a request
    client.get("/api/products", headers=auth(buyer_token))

    db_session.expire_all()
    count = db_session.query(AuditLog).filter(AuditLog.path == "/api/products").count()
    assert count >= 1
