"""Tests for RAG ingestion — idempotency and collection counts.

Uses chromadb.EphemeralClient (in-memory) + real sentence-transformers model.
Requires: uv sync --extra rag --group dev
"""

import os

import chromadb
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.persistence.models import Base
from app.infrastructure.rag.collections import (
    get_or_create_faq_collection,
    get_or_create_products_collection,
)
from app.infrastructure.rag.faq_data import FAQ_ITEMS
from app.infrastructure.rag.ingest import ingest_faq, ingest_products


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


@pytest.fixture
def chroma() -> chromadb.ClientAPI:
    return chromadb.EphemeralClient()


# ---------------------------------------------------------------------------
# FAQ ingestion
# ---------------------------------------------------------------------------


def test_faq_ingestion_count(chroma: chromadb.ClientAPI) -> None:
    ingest_faq(chroma)
    collection = get_or_create_faq_collection(chroma)
    assert collection.count() == len(FAQ_ITEMS)


def test_faq_ingestion_idempotent(chroma: chromadb.ClientAPI) -> None:
    ingest_faq(chroma)
    ingest_faq(chroma)
    collection = get_or_create_faq_collection(chroma)
    assert collection.count() == len(FAQ_ITEMS)


# ---------------------------------------------------------------------------
# Products ingestion
# ---------------------------------------------------------------------------


def test_products_ingestion_count(chroma: chromadb.ClientAPI, db_session) -> None:
    n = ingest_products(chroma, db_session)
    collection = get_or_create_products_collection(chroma)
    # 100 normal + 5 poisoned
    assert n == 105
    assert collection.count() == 105


def test_products_ingestion_idempotent(chroma: chromadb.ClientAPI, db_session) -> None:
    ingest_products(chroma, db_session)
    ingest_products(chroma, db_session)
    collection = get_or_create_products_collection(chroma)
    assert collection.count() == 105


def test_poisoned_products_present(chroma: chromadb.ClientAPI, db_session) -> None:
    from scripts.seed import POISONED_PRODUCT_IDS

    ingest_products(chroma, db_session)
    collection = get_or_create_products_collection(chroma)

    poisoned_doc_ids = [f"product_{pid}" for pid in POISONED_PRODUCT_IDS]
    result = collection.get(ids=poisoned_doc_ids, include=["metadatas"])
    assert len(result["ids"]) == 5
