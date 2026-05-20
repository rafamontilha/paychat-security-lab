from functools import lru_cache

from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def embed(texts: list[str]) -> list[list[float]]:
    result: list[list[float]] = _get_model().encode(texts).tolist()  # type: ignore[assignment]
    return result
