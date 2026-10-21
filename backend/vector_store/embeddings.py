from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """Load the embedding model once and reuse it."""
    return SentenceTransformer(MODEL_NAME)


def embed_texts(texts: list[str]) -> np.ndarray:
    """Convert a list of text chunks into normalized embedding vectors."""
    if not texts:
        return np.empty((0, EMBEDDING_DIMENSION), dtype=np.float32)

    if any(not isinstance(text, str) or not text.strip() for text in texts):
        raise ValueError("Every input must be a non-empty string.")

    vectors = get_embedding_model().encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    vectors = np.asarray(vectors, dtype=np.float32)

    if vectors.shape != (len(texts), EMBEDDING_DIMENSION):
        raise ValueError(
            f"Unexpected embedding shape: {vectors.shape}"
        )

    if not np.isfinite(vectors).all():
        raise ValueError("Embedding vectors contain invalid numeric values.")

    return vectors


def embed_query(query: str) -> np.ndarray:
    """Convert a search query into one normalized embedding vector."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Query must be a non-empty string.")

    return embed_texts([query])[0]
