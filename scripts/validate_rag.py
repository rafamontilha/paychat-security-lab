#!/usr/bin/env python
# ruff: noqa: E402, I001
"""CLI para inspecionar chunks retornados pelo RAG.

Usage:
    python scripts/validate_rag.py "<query>" [--collection products|faq] [--top-k N]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from app.infrastructure.rag.client import get_chroma_client
from app.infrastructure.rag.collections import (
    get_or_create_faq_collection,
    get_or_create_products_collection,
)
from app.infrastructure.rag.embedder import embed


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate RAG retrieval")
    parser.add_argument("query", help="Query text")
    parser.add_argument("--collection", choices=["products", "faq"], default="products")
    parser.add_argument("--top-k", type=int, default=5, dest="top_k")
    args = parser.parse_args()

    client = get_chroma_client()
    collection = (
        get_or_create_products_collection(client)
        if args.collection == "products"
        else get_or_create_faq_collection(client)
    )

    query_vec = embed([args.query])[0]
    results = collection.query(
        query_embeddings=[query_vec],
        n_results=args.top_k,
        include=["documents", "metadatas", "distances"],
    )

    ids = results["ids"][0] if results["ids"] else []
    documents = (results["documents"] or [[]])[0]
    metadatas = (results["metadatas"] or [[]])[0]
    distances = (results["distances"] or [[]])[0]

    print(f"\nQuery    : {args.query!r}")
    print(f"Coleção  : {args.collection}  |  top-{args.top_k}\n")
    print("-" * 72)

    if not ids:
        print("Nenhum resultado encontrado.")
        return

    for rank, doc_id in enumerate(ids, start=1):
        text = documents[rank - 1] if rank - 1 < len(documents) else ""
        meta = metadatas[rank - 1] if rank - 1 < len(metadatas) else {}
        dist = distances[rank - 1] if rank - 1 < len(distances) else None
        score = round(1.0 - dist, 4) if dist is not None else "n/a"

        preview = (text or "")[:120].replace("\n", " ")
        if len(text or "") > 120:
            preview += "…"

        print(f"#{rank:02d}  id={doc_id}  score={score}")
        print(f"     {preview}")
        if meta:
            meta_str = "  ".join(f"{k}={v}" for k, v in meta.items())
            print(f"     [{meta_str}]")
        print()


if __name__ == "__main__":
    main()
