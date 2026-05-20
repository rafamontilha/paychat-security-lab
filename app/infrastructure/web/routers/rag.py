from typing import Literal

import chromadb
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.infrastructure.rag.client import get_chroma_client
from app.infrastructure.rag.collections import (
    get_or_create_faq_collection,
    get_or_create_products_collection,
)
from app.infrastructure.rag.embedder import embed
from app.infrastructure.web.dependencies import ActorContext

router = APIRouter(prefix="/api/rag", tags=["rag"])


class RagSearchRequest(BaseModel):
    query: str
    collection: Literal["products", "faq"] = "products"
    top_k: int = 5


class RagChunk(BaseModel):
    id: str
    text: str
    metadata: dict
    score: float


class RagSearchResponse(BaseModel):
    chunks: list[RagChunk]
    collection: str


@router.post("/search", response_model=RagSearchResponse)
def rag_search(
    body: RagSearchRequest,
    actor: ActorContext,
    chroma: chromadb.ClientAPI = Depends(get_chroma_client),
) -> RagSearchResponse:
    collection = (
        get_or_create_products_collection(chroma)
        if body.collection == "products"
        else get_or_create_faq_collection(chroma)
    )

    query_vec = embed([body.query])[0]
    results = collection.query(
        query_embeddings=[query_vec],
        n_results=body.top_k,
        include=["documents", "metadatas", "distances"],
    )

    ids: list[str] = results["ids"][0] if results["ids"] else []
    documents: list[str | None] = (results["documents"] or [[]])[0]
    metadatas: list[dict | None] = (results["metadatas"] or [[]])[0]  # type: ignore[assignment]
    distances: list[float | None] = (results["distances"] or [[]])[0]  # type: ignore[assignment]

    chunks = []
    for i, doc_id in enumerate(ids):
        dist = distances[i] if i < len(distances) else None
        score = round(1.0 - dist, 4) if dist is not None else 0.0
        raw_meta = metadatas[i] if i < len(metadatas) else None
        meta: dict = dict(raw_meta) if raw_meta is not None else {}
        chunks.append(
            RagChunk(
                id=doc_id,
                text=documents[i] or "" if i < len(documents) else "",
                metadata=meta,
                score=score,
            )
        )

    return RagSearchResponse(chunks=chunks, collection=body.collection)
