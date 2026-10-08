def create_chunks(
    text: str,
    chunk_size: int = 200,
    overlap: int = 30
) -> list[dict]:
    """
    Split cleaned text into overlapping chunks.

    chunk_size:
        Maximum number of words in each chunk.

    overlap:
        Number of words shared between consecutive chunks.
    """

    if not text.strip():
        return []

    words = text.split()

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks = []

    start = 0
    chunk_number = 1

    while start < len(words):

        end = min(start + chunk_size, len(words))

        chunk_text = " ".join(words[start:end])

        chunks.append({
            "chunk_id": f"chunk_{chunk_number:03d}",
            "text": chunk_text,
            "start_word": start,
            "end_word": end
        })

        chunk_number += 1

        if end == len(words):
            break

        start = end - overlap

    return chunks