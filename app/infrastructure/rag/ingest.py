"""Core ingest logic — used by scripts/ingest_rag.py and the POST /api/products hook."""

import chromadb
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import Product
from app.infrastructure.rag.collections import (
    get_or_create_faq_collection,
    get_or_create_products_collection,
)
from app.infrastructure.rag.embedder import embed
from app.infrastructure.rag.faq_data import FAQ_ITEMS

_BATCH = 32


def ingest_products(client: chromadb.ClientAPI, db: Session) -> int:
    collection = get_or_create_products_collection(client)
    products: list[Product] = db.query(Product).all()

    ids, documents, metadatas = [], [], []
    for p in products:
        text = f"{p.title}: {p.description}"
        ids.append(f"product_{p.id}")
        documents.append(text)
        metadatas.append(
            {
                "product_id": p.id,
                "seller_id": p.seller_id,
                "category": p.category,
                "created_at": p.created_at.isoformat(),
                "is_poisoned": getattr(p, "is_poisoned", False),
            }
        )

    for i in range(0, len(ids), _BATCH):
        batch_ids = ids[i : i + _BATCH]
        batch_docs = documents[i : i + _BATCH]
        batch_meta = metadatas[i : i + _BATCH]
        batch_vecs = embed(batch_docs)
        collection.upsert(
            ids=batch_ids,
            documents=batch_docs,
            embeddings=batch_vecs,
            metadatas=batch_meta,
        )

    return len(ids)


def ingest_single_product(
    client: chromadb.ClientAPI,
    product: Product,
    is_poisoned: bool = False,
) -> None:
    collection = get_or_create_products_collection(client)
    text = f"{product.title}: {product.description}"
    vector = embed([text])[0]
    collection.upsert(
        ids=[f"product_{product.id}"],
        documents=[text],
        embeddings=[vector],
        metadatas=[
            {
                "product_id": product.id,
                "seller_id": product.seller_id,
                "category": product.category,
                "created_at": product.created_at.isoformat(),
                "is_poisoned": is_poisoned,
            }
        ],
    )


def ingest_faq(client: chromadb.ClientAPI) -> int:
    collection = get_or_create_faq_collection(client)
    ids, documents, metadatas = [], [], []

    for faq_id, (topic, question, answer) in enumerate(FAQ_ITEMS, start=1):
        text = f"{question}\n{answer}"
        ids.append(f"faq_{faq_id}")
        documents.append(text)
        metadatas.append({"faq_id": faq_id, "topic": topic})

    for i in range(0, len(ids), _BATCH):
        batch_ids = ids[i : i + _BATCH]
        batch_docs = documents[i : i + _BATCH]
        batch_meta = metadatas[i : i + _BATCH]
        batch_vecs = embed(batch_docs)
        collection.upsert(
            ids=batch_ids,
            documents=batch_docs,
            embeddings=batch_vecs,
            metadatas=batch_meta,
        )

    return len(ids)
