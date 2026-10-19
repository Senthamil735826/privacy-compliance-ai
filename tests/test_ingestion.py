import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.ingestion.cleaner import clean_text
from backend.ingestion.chunker import create_chunks


def test_clean_text():
    sample_text = """
    This    is    a sample privacy policy.

    We collect name, email address, location
    and device information.
    """
    cleaned = clean_text(sample_text)
    assert "This is a sample privacy policy." in cleaned
    assert "We collect name, email address, location" in cleaned
    assert "  " not in cleaned


def test_create_chunks():
    sample_text = "This is a sample privacy policy for chunking testing."
    chunks = create_chunks(sample_text, chunk_size=20, overlap=5)
    assert len(chunks) > 1
    for chunk in chunks:
        assert "chunk_id" in chunk
        assert "text" in chunk
        assert "start" in chunk
        assert "end" in chunk
