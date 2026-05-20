#!/usr/bin/env python
# ruff: noqa: E402, I001
"""Ingest products and FAQ into ChromaDB. Idempotent via upsert — safe to run multiple times."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy.orm import sessionmaker

from app.infrastructure.persistence.database import get_engine
from app.infrastructure.rag.client import get_chroma_client
from app.infrastructure.rag.ingest import ingest_faq, ingest_products

if __name__ == "__main__":
    client = get_chroma_client()
    engine = get_engine()
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as db:
        n_products = ingest_products(client, db)
        n_faq = ingest_faq(client)

    print(f"Ingestão concluída: {n_products} produtos, {n_faq} FAQ no ChromaDB.")
