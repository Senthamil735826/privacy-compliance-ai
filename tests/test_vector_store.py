import sys
import tempfile
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.vector_store.embeddings import embed_texts, embed_query, EMBEDDING_DIMENSION
from backend.vector_store.faiss_store import FaissVectorStore
from backend.vector_store.search_service import SemanticSearchService


# ============================================================================
# 1. EMBEDDING FUNCTIONALITY TESTS
# ============================================================================

def test_embed_texts_valid():
    texts = [
        "We collect personal information to provide our services.",
        "We retain personal data only as long as necessary.",
    ]
    vectors = embed_texts(texts)
    assert isinstance(vectors, np.ndarray)
    assert vectors.shape == (2, EMBEDDING_DIMENSION)
    assert vectors.dtype == np.float32
    assert np.isfinite(vectors).all()

    # Check normalization: each vector has L2 norm ~ 1.0
    norms = np.linalg.norm(vectors, axis=1)
    for norm in norms:
        assert np.isclose(norm, 1.0, atol=1e-5)


def test_embed_texts_empty():
    vectors = embed_texts([])
    assert isinstance(vectors, np.ndarray)
    assert vectors.shape == (0, EMBEDDING_DIMENSION)


def test_embed_texts_invalid_inputs():
    with pytest.raises(ValueError, match="Every input must be a non-empty string"):
        embed_texts(["Valid text", ""])

    with pytest.raises(ValueError, match="Every input must be a non-empty string"):
        embed_texts(["Valid text", "   "])

    with pytest.raises(ValueError, match="Every input must be a non-empty string"):
        embed_texts(["Valid text", None])


def test_embed_query_valid():
    query = "How long do you keep personal data?"
    vector = embed_query(query)
    assert isinstance(vector, np.ndarray)
    assert vector.shape == (EMBEDDING_DIMENSION,)
    assert vector.dtype == np.float32
    assert np.isfinite(vector).all()
    assert np.isclose(np.linalg.norm(vector), 1.0, atol=1e-5)


def test_embed_query_invalid():
    with pytest.raises(ValueError, match="Query must be a non-empty string"):
        embed_query("")

    with pytest.raises(ValueError, match="Query must be a non-empty string"):
        embed_query("    ")

    with pytest.raises(ValueError, match="Query must be a non-empty string"):
        embed_query(None)


# ============================================================================
# 2. FAISS VECTOR STORE TESTS
# ============================================================================

def test_faiss_store_add_and_search():
    store = FaissVectorStore(dimension=4)
    chunks = [
        {"chunk_id": 1, "text": "First chunk", "start": 0, "end": 10},
        {"chunk_id": 2, "text": "Second chunk", "start": 10, "end": 20},
    ]
    vectors = np.array([
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
    ], dtype=np.float32)

    store.add_chunks(chunks, vectors)
    assert store.index.ntotal == 2
    assert len(store.chunks) == 2

    # Query closest to first chunk
    query = np.array([1.0, 0.1, 0.0, 0.0], dtype=np.float32)
    results = store.search(query, top_k=1)
    assert len(results) == 1
    assert results[0]["chunk"]["chunk_id"] == 1
    assert results[0]["similarity"] > 0.9


def test_faiss_store_top_k_limits():
    store = FaissVectorStore(dimension=4)
    chunks = [{"chunk_id": 1, "text": "Only chunk", "start": 0, "end": 10}]
    vectors = np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32)
    store.add_chunks(chunks, vectors)

    # top_k greater than index size returns all available items
    results = store.search(np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32), top_k=5)
    assert len(results) == 1

    with pytest.raises(ValueError, match="top_k must be positive"):
        store.search(np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32), top_k=0)


def test_faiss_store_empty_index():
    store = FaissVectorStore(dimension=4)
    results = store.search(np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32), top_k=3)
    assert results == []


def test_faiss_store_invalid_dimension():
    with pytest.raises(ValueError, match="Dimension must be positive"):
        FaissVectorStore(dimension=0)


def test_faiss_store_invalid_vectors():
    store = FaissVectorStore(dimension=4)
    chunks = [{"chunk_id": 1, "text": "Chunk", "start": 0, "end": 5}]

    # Wrong shape (1D instead of 2D)
    with pytest.raises(ValueError, match="Embeddings must be a two-dimensional array"):
        store.add_chunks(chunks, np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32))

    # Wrong dimension (dim=3 instead of 4)
    with pytest.raises(ValueError, match="number of embeddings and their dimensions must match"):
        store.add_chunks(chunks, np.array([[1.0, 0.0, 0.0]], dtype=np.float32))

    # Length mismatch
    with pytest.raises(ValueError, match="number of embeddings and their dimensions must match"):
        store.add_chunks(chunks, np.array([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]], dtype=np.float32))

    # Non-finite values
    with pytest.raises(ValueError, match="Embeddings contain invalid numeric values"):
        store.add_chunks(chunks, np.array([[np.nan, 0.0, 0.0, 0.0]], dtype=np.float32))


def test_faiss_store_invalid_query():
    store = FaissVectorStore(dimension=4)
    chunks = [{"chunk_id": 1, "text": "Chunk", "start": 0, "end": 5}]
    store.add_chunks(chunks, np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32))

    # Wrong query shape
    with pytest.raises(ValueError, match="Query embedding must have shape"):
        store.search(np.array([1.0, 0.0, 0.0], dtype=np.float32))

    # Non-finite query
    with pytest.raises(ValueError, match="Query embedding contains invalid numeric values"):
        store.search(np.array([np.inf, 0.0, 0.0, 0.0], dtype=np.float32))

    # Zero vector
    with pytest.raises(ValueError, match="Query embedding cannot be a zero vector"):
        store.search(np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float32))


def test_faiss_store_invalid_chunk_metadata():
    store = FaissVectorStore(dimension=4)
    vectors = np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32)

    with pytest.raises(ValueError, match="Every chunk must be a dictionary containing text"):
        store.add_chunks(["not a dict"], vectors)

    with pytest.raises(ValueError, match="Every chunk must be a dictionary containing text"):
        store.add_chunks([{"no_text": 123}], vectors)

    with pytest.raises(ValueError, match="Every chunk must contain non-empty text"):
        store.add_chunks([{"text": "   "}], vectors)


def test_faiss_store_save_and_load():
    store = FaissVectorStore(dimension=4)
    chunks = [
        {"chunk_id": 10, "text": "Sample text alpha", "start": 0, "end": 17},
        {"chunk_id": 20, "text": "Sample text beta", "start": 18, "end": 34},
    ]
    vectors = np.array([
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
    ], dtype=np.float32)
    store.add_chunks(chunks, vectors)

    with tempfile.TemporaryDirectory() as temp_dir:
        store.save(temp_dir)
        loaded = FaissVectorStore.load(temp_dir)

        assert loaded.dimension == 4
        assert loaded.index.ntotal == 2
        assert len(loaded.chunks) == 2
        assert loaded.chunks[0]["chunk_id"] == 10
        assert loaded.chunks[1]["text"] == "Sample text beta"

        results = loaded.search(np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32), top_k=1)
        assert len(results) == 1
        assert results[0]["chunk"]["chunk_id"] == 10


# ============================================================================
# 3. SEMANTIC SEARCH SERVICE TESTS
# ============================================================================

def test_search_service_multi_document_isolation():
    service = SemanticSearchService()

    doc1_chunks = [
        {"chunk_id": 1, "text": "Apple fruit orchard harvest and seeds.", "start": 0, "end": 38},
        {"chunk_id": 2, "text": "Growing organic apples in Washington state.", "start": 39, "end": 81},
    ]
    doc2_chunks = [
        {"chunk_id": 1, "text": "Deep sea marine biology and ocean coral reefs.", "start": 0, "end": 46},
        {"chunk_id": 2, "text": "Dolphins and whales migrate in Pacific waters.", "start": 47, "end": 93},
    ]

    count1 = service.index_document("doc-apples", doc1_chunks)
    count2 = service.index_document("doc-oceans", doc2_chunks)

    assert count1 == 2
    assert count2 == 2
    assert service.has_document("doc-apples")
    assert service.has_document("doc-oceans")

    # Search doc-apples for ocean query -> searches only doc-apples chunks
    results_apples = service.search("doc-apples", "deep sea coral reefs", top_k=2)
    assert len(results_apples) == 2
    for r in results_apples:
        assert "apple" in r["text"].lower()

    # Search doc-oceans for apple query -> searches only doc-oceans chunks
    results_oceans = service.search("doc-oceans", "fresh organic apples", top_k=2)
    assert len(results_oceans) == 2
    for r in results_oceans:
        assert "sea" in r["text"].lower() or "ocean" in r["text"].lower() or "dolphins" in r["text"].lower()


def test_search_service_document_removal_and_independence():
    service = SemanticSearchService()

    chunks_a = [{"chunk_id": 1, "text": "Document A privacy statement.", "start": 0, "end": 30}]
    chunks_b = [{"chunk_id": 1, "text": "Document B security protocols.", "start": 0, "end": 31}]

    service.index_document("doc-a", chunks_a)
    service.index_document("doc-b", chunks_b)

    assert service.has_document("doc-a")
    assert service.has_document("doc-b")

    # Remove doc-a
    removed = service.remove_document("doc-a")
    assert removed is True
    assert not service.has_document("doc-a")

    # doc-b remains completely intact
    assert service.has_document("doc-b")
    b_results = service.search("doc-b", "security protocols", top_k=1)
    assert len(b_results) == 1
    assert "Document B" in b_results[0]["text"]

    # Removing doc-a again returns False
    assert service.remove_document("doc-a") is False


def test_search_service_atomic_replacement():
    service = SemanticSearchService()

    initial_chunks = [{"chunk_id": 1, "text": "Initial valid text content.", "start": 0, "end": 27}]
    service.index_document("doc-atomic", initial_chunks)

    # Attempt replacement with invalid chunks (missing non-empty text)
    with pytest.raises(ValueError):
        service.index_document("doc-atomic", [{"chunk_id": 2, "text": "   "}])

    # Previous valid index must still be intact
    assert service.has_document("doc-atomic")
    results = service.search("doc-atomic", "initial valid text", top_k=1)
    assert len(results) == 1
    assert "Initial valid text" in results[0]["text"]


def test_search_service_input_validation():
    service = SemanticSearchService()

    # Invalid document_id for index
    with pytest.raises(ValueError, match="document_id must be a non-empty string"):
        service.index_document("", [{"chunk_id": 1, "text": "text"}])

    # Empty chunks
    with pytest.raises(ValueError, match="At least one chunk is required"):
        service.index_document("doc-1", [])

    # Non-dict chunk
    with pytest.raises(ValueError, match="Every chunk must be a dictionary"):
        service.index_document("doc-1", ["not-a-dict"])

    # Search unknown doc
    with pytest.raises(KeyError, match="No indexed document found for ID"):
        service.search("nonexistent-doc", "query")

    # Search empty query
    with pytest.raises(ValueError, match="query must be a non-empty string"):
        service.search("doc-1", "   ")

    # Search invalid top_k
    chunks = [{"chunk_id": 1, "text": "Some text", "start": 0, "end": 9}]
    service.index_document("doc-1", chunks)

    with pytest.raises(ValueError, match="top_k must be a positive integer"):
        service.search("doc-1", "query", top_k=0)

    with pytest.raises(ValueError, match="top_k must be a positive integer"):
        service.search("doc-1", "query", top_k=True)  # bool is not accepted as int
