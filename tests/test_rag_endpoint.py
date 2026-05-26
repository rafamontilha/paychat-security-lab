"""Integration tests for POST /api/rag/search and POST /api/products (Chroma hook).

Uses chromadb.EphemeralClient overriding the FastAPI dependency, + real embedder.
Requires: uv sync --extra rag --group dev
"""

import os

import chromadb
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models import Base, Role, User
from app.infrastructure.rag.client import get_chroma_client
from app.infrastructure.rag.ingest import ingest_faq, ingest_products
from app.infrastructure.web.fastapi_app import app

# ---------------------------------------------------------------------------
# Session-scoped fixtures (DB + seed + Chroma pre-populated)
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
    from scripts.seed import seed

    seed(db_session)


@pytest.fixture(scope="session")
def chroma_client() -> chromadb.ClientAPI:
    """Shared in-memory Chroma client pre-populated with products + FAQ."""
    # chromadb 1.x EphemeralClient shares one in-memory store process-wide; clear
    # collections so this module's catalog isn't polluted by other test files.
    client = chromadb.EphemeralClient()
    for col in client.list_collections():
        client.delete_collection(col.name)
    return client


@pytest.fixture(scope="session", autouse=True)
def populate_chroma(chroma_client: chromadb.ClientAPI, db_session) -> list[int]:
    ingest_products(chroma_client, db_session)
    ingest_faq(chroma_client)
    # Capture poison IDs tied to the exact seed/DB state ingested into Chroma, so the
    # assertion can't desync from a later seed() call mutating the module-global list.
    from scripts.seed import POISONED_PRODUCT_IDS

    return list(POISONED_PRODUCT_IDS)


@pytest.fixture(scope="session")
def client(db_engine, chroma_client: chromadb.ClientAPI) -> TestClient:
    Session = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)

    def override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_chroma_client] = lambda: chroma_client

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def buyer_token(client: TestClient, db_session) -> str:
    buyer = db_session.query(User).filter(User.role == Role.buyer).first()
    resp = client.post("/api/auth/login", json={"api_key": buyer.api_key})
    assert resp.status_code == 200
    return resp.json()["session_token"]


@pytest.fixture(scope="session")
def seller_token(client: TestClient, db_session) -> str:
    seller = db_session.query(User).filter(User.role == Role.seller).first()
    resp = client.post("/api/auth/login", json={"api_key": seller.api_key})
    assert resp.status_code == 200
    return resp.json()["session_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# POST /api/rag/search — authentication
# ---------------------------------------------------------------------------


def test_rag_search_requires_auth(client: TestClient) -> None:
    resp = client.post("/api/rag/search", json={"query": "reembolso"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/rag/search — FAQ collection
# ---------------------------------------------------------------------------


def test_rag_faq_reembolso_top3(client: TestClient, buyer_token: str) -> None:
    resp = client.post(
        "/api/rag/search",
        json={"query": "como solicito reembolso", "collection": "faq", "top_k": 3},
        headers=auth(buyer_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["collection"] == "faq"
    assert len(data["chunks"]) >= 1
    topics = [c["metadata"].get("topic") for c in data["chunks"]]
    assert "reembolso" in topics, f"Expected 'reembolso' topic in top-3, got: {topics}"


def test_rag_faq_entrega(client: TestClient, buyer_token: str) -> None:
    resp = client.post(
        "/api/rag/search",
        json={"query": "qual a previsão de entrega do meu pedido", "collection": "faq", "top_k": 3},
        headers=auth(buyer_token),
    )
    assert resp.status_code == 200
    topics = [c["metadata"].get("topic") for c in resp.json()["chunks"]]
    assert "entrega" in topics, f"Expected 'entrega' topic in top-3, got: {topics}"


# ---------------------------------------------------------------------------
# POST /api/rag/search — products collection + poisoning
# ---------------------------------------------------------------------------


def test_rag_products_tenis_returns_poisoned(
    client: TestClient, buyer_token: str, populate_chroma: list[int]
) -> None:
    poisoned_ids = populate_chroma  # captured at ingest time → matches Chroma contents

    resp = client.post(
        "/api/rag/search",
        json={"query": "tênis", "collection": "products", "top_k": 10},
        headers=auth(buyer_token),
    )
    assert resp.status_code == 200
    chunks = resp.json()["chunks"]
    assert len(chunks) >= 1

    returned_product_ids = {
        int(c["id"].split("_")[1]) for c in chunks if c["id"].startswith("product_")
    }
    overlap = returned_product_ids & set(poisoned_ids)
    assert overlap, (
        f"Expected ≥1 poisoned product ID {poisoned_ids} in top-10, "
        f"got product IDs: {sorted(returned_product_ids)}"
    )


def test_rag_products_out_of_domain(client: TestClient, buyer_token: str) -> None:
    """Out-of-domain query must not crash; may return low-score chunks."""
    resp = client.post(
        "/api/rag/search",
        json={"query": "pizza margherita", "collection": "products", "top_k": 5},
        headers=auth(buyer_token),
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST /api/products — Chroma hook (upsert after create)
# ---------------------------------------------------------------------------


def test_create_product_ingests_into_chroma(
    client: TestClient, seller_token: str, chroma_client: chromadb.ClientAPI
) -> None:
    from app.infrastructure.rag.collections import get_or_create_products_collection

    resp = client.post(
        "/api/products",
        json={
            "title": "Bicicleta de Montanha Turbo",
            "description": "Suspensão dianteira, 21 marchas, quadro de alumínio.",
            "price": 1299.00,
            "category": "Esportes",
        },
        headers=auth(seller_token),
    )
    assert resp.status_code == 201
    product_id = resp.json()["id"]

    collection = get_or_create_products_collection(chroma_client)
    result = collection.get(ids=[f"product_{product_id}"])
    assert result["ids"] == [f"product_{product_id}"]


def test_create_product_forbidden_for_buyer(client: TestClient, buyer_token: str) -> None:
    resp = client.post(
        "/api/products",
        json={
            "title": "Produto Indevido",
            "description": "Comprador tentando criar produto.",
            "price": 10.0,
            "category": "Livros",
        },
        headers=auth(buyer_token),
    )
    assert resp.status_code == 403


def test_create_product_searchable_after_ingest(client: TestClient, seller_token: str) -> None:
    """Product created via REST appears in RAG search in the same session."""
    unique_title = "Violão Clássico Cedro Natural Exclusivo"
    resp = client.post(
        "/api/products",
        json={
            "title": unique_title,
            "description": "Instrumento artesanal de alta qualidade para concertistas.",
            "price": 899.00,
            "category": "Livros",
        },
        headers=auth(seller_token),
    )
    assert resp.status_code == 201

    search_resp = client.post(
        "/api/rag/search",
        json={"query": "violão clássico cedro", "collection": "products", "top_k": 5},
        headers=auth(seller_token),
    )
    assert search_resp.status_code == 200
    texts = [c["text"] for c in search_resp.json()["chunks"]]
    assert any(unique_title in t for t in texts), f"New product not found in RAG. Got: {texts[:2]}"
