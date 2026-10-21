from typing import Any

try:
    from backend.vector_store.embeddings import embed_texts, embed_query
    from backend.vector_store.faiss_store import FaissVectorStore
except ImportError:
    from vector_store.embeddings import embed_texts, embed_query
    from vector_store.faiss_store import FaissVectorStore


class SemanticSearchService:
    """Perform semantic searches within individual policy documents."""

    def __init__(self) -> None:
        # Each document has its own FAISS index.
        self._stores: dict[str, FaissVectorStore] = {}

    def index_document(
        self,
        document_id: str,
        chunks: list[dict[str, Any]],
    ) -> int:
        """Create a document-specific FAISS index from policy chunks."""

        if not isinstance(document_id, str) or not document_id.strip():
            raise ValueError("document_id must be a non-empty string.")

        clean_doc_id = document_id.strip()

        if not isinstance(chunks, list) or not chunks:
            raise ValueError("At least one chunk is required.")

        for chunk in chunks:
            if not isinstance(chunk, dict):
                raise ValueError("Every chunk must be a dictionary.")
            text_val = chunk.get("text")
            if not isinstance(text_val, str) or not text_val.strip():
                raise ValueError("Every chunk must contain non-empty text.")

        # Extract text from each chunk.
        texts = [chunk["text"] for chunk in chunks]

        # Generate normalized embedding vectors.
        embeddings = embed_texts(texts)

        # Build a separate FAISS index for this document.
        store = FaissVectorStore()
        store.add_chunks(chunks, embeddings)

        # Register the document only after indexing succeeds (atomic update).
        self._stores[clean_doc_id] = store

        return store.index.ntotal

    def has_document(self, document_id: str) -> bool:
        """Check whether a document has an in-memory index."""

        if not isinstance(document_id, str) or not document_id.strip():
            return False

        return document_id.strip() in self._stores

    def search(
        self,
        document_id: str,
        query: str,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """Search only the specified document's indexed chunks."""

        if not isinstance(document_id, str) or not document_id.strip():
            raise ValueError("document_id must be a non-empty string.")

        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string.")

        if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
            raise ValueError("top_k must be a positive integer.")

        clean_doc_id = document_id.strip()
        clean_query = query.strip()

        store = self._stores.get(clean_doc_id)

        if store is None:
            raise KeyError(
                f"No indexed document found for ID: {clean_doc_id}"
            )

        # Convert the user's query into an embedding.
        query_embedding = embed_query(clean_query)

        # Retrieve the most relevant chunks.
        results = store.search(
            query_embedding,
            top_k=top_k,
        )

        return [
            {
                "chunk_id": result["chunk"].get("chunk_id"),
                "text": result["chunk"]["text"],
                "start": result["chunk"].get("start"),
                "end": result["chunk"].get("end"),
                "similarity": result["similarity"],
            }
            for result in results
        ]

    def remove_document(self, document_id: str) -> bool:
        """Remove one document's in-memory index."""

        if not isinstance(document_id, str) or not document_id.strip():
            return False

        return self._stores.pop(document_id.strip(), None) is not None