import json
from pathlib import Path

import faiss
import numpy as np


class FaissVectorStore:
    """Store and search policy chunk embeddings using FAISS."""

    def __init__(self, dimension: int = 384):
        if dimension <= 0:
            raise ValueError("Dimension must be positive.")

        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)
        self.chunks: list[dict] = []

    def add_chunks(
        self,
        chunks: list[dict],
        embeddings: np.ndarray,
    ) -> None:
        """Add embeddings and their corresponding chunk metadata."""
        if not chunks:
            if len(embeddings) != 0:
                raise ValueError("Chunks and embeddings must have equal lengths.")
            return

        vectors = np.asarray(embeddings, dtype=np.float32)

        if vectors.ndim != 2:
            raise ValueError("Embeddings must be a two-dimensional array.")

        if vectors.shape != (len(chunks), self.dimension):
            raise ValueError(
                "The number of embeddings and their dimensions must "
                "match the supplied chunks."
            )

        if not np.isfinite(vectors).all():
            raise ValueError("Embeddings contain invalid numeric values.")

        if any(not isinstance(chunk, dict) or "text" not in chunk for chunk in chunks):
            raise ValueError("Every chunk must be a dictionary containing text.")

        if any(not isinstance(chunk["text"], str) or not chunk["text"].strip()
               for chunk in chunks):
            raise ValueError("Every chunk must contain non-empty text.")

        vectors = vectors.copy()
        faiss.normalize_L2(vectors)

        self.index.add(vectors)
        self.chunks.extend(dict(chunk) for chunk in chunks)

    def search(self, query_embedding: np.ndarray, top_k: int = 3) -> list[dict]:
        """Return the most relevant chunks for a query embedding."""
        if top_k <= 0:
            raise ValueError("top_k must be positive.")

        if self.index.ntotal == 0:
            return []

        query = np.asarray(query_embedding, dtype=np.float32)

        if query.shape == (self.dimension,):
            query = query.reshape(1, -1)

        if query.shape != (1, self.dimension):
            raise ValueError(
                f"Query embedding must have shape ({self.dimension},)."
            )

        if not np.isfinite(query).all():
            raise ValueError("Query embedding contains invalid numeric values.")

        if np.linalg.norm(query) == 0:
            raise ValueError("Query embedding cannot be a zero vector.")

        faiss.normalize_L2(query)

        count = min(top_k, self.index.ntotal)
        scores, indices = self.index.search(query, count)

        results = []

        for score, index_id in zip(scores[0], indices[0]):
            if index_id < 0:
                continue

            results.append({
                "chunk": self.chunks[int(index_id)],
                "similarity": float(score),
            })

        return results

    def save(self, directory: str | Path) -> None:
        """Save the FAISS index and chunk metadata to a directory."""
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)

        faiss.write_index(self.index, str(directory / "index.faiss"))

        with (directory / "chunks.json").open("w", encoding="utf-8") as file:
            json.dump(self.chunks, file, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, directory: str | Path) -> "FaissVectorStore":
        """Load a previously saved FAISS index and its chunk metadata."""
        directory = Path(directory)

        index_path = directory / "index.faiss"
        chunks_path = directory / "chunks.json"

        if not index_path.is_file() or not chunks_path.is_file():
            raise FileNotFoundError(
                f"FAISS index or chunk metadata not found in {directory}."
            )

        index = faiss.read_index(str(index_path))

        with chunks_path.open("r", encoding="utf-8") as file:
            chunks = json.load(file)

        if not isinstance(chunks, list) or len(chunks) != index.ntotal:
            raise ValueError("Saved chunk metadata does not match the FAISS index.")

        store = cls(dimension=index.d)
        store.index = index
        store.chunks = chunks

        return store
