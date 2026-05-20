import chromadb
from langchain_core.tools import tool

from app.infrastructure.rag.collections import get_or_create_products_collection
from app.infrastructure.rag.embedder import embed


def make_search_products_tool(chroma: chromadb.ClientAPI):
    @tool("search_products")
    def search_products(query: str) -> str:
        """Search the marketplace product catalog using semantic search.

        Args:
            query: Natural language search query describing the product
        """
        collection = get_or_create_products_collection(chroma)
        query_vec = embed([query])[0]
        results = collection.query(
            query_embeddings=[query_vec],
            n_results=5,
            include=["documents", "metadatas", "distances"],
        )

        ids: list[str] = results["ids"][0] if results["ids"] else []
        metadatas: list = (results["metadatas"] or [[]])[0]
        distances: list = (results["distances"] or [[]])[0]

        if not ids:
            return "No products found for this query."

        lines = []
        for i, doc_id in enumerate(ids):
            meta = metadatas[i] if i < len(metadatas) and metadatas[i] else {}
            dist = distances[i] if i < len(distances) else 1.0
            score = round(1.0 - float(dist), 3)
            lines.append(
                f"id={doc_id} category={meta.get('category', '?')} "
                f"score={score} poisoned={meta.get('is_poisoned', False)}"
            )

        return "\n".join(lines)

    return search_products
