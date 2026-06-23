"""Text embeddings for the regulation corpus (GraphRAG retrieval layer).

Uses fastembed (ONNX runtime — no torch) with `all-MiniLM-L6-v2` (384-dim),
the same model + dimension convention as the other Samyama KGs. Real embeddings:
if fastembed is unavailable we raise rather than fabricate vectors (no mocks).
"""
from __future__ import annotations

from functools import lru_cache

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DIM = 384


@lru_cache(maxsize=1)
def _model():
    try:
        from fastembed import TextEmbedding
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "fastembed is required for embeddings: pip install fastembed "
            "(or install the project with the embedding extra)."
        ) from e
    return TextEmbedding(MODEL_NAME)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of strings -> list of 384-float vectors."""
    return [[float(x) for x in v] for v in _model().embed(list(texts))]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
