def create_chunks(
    text: str,
    chunk_size: int = 1500,
    overlap: int = 200
) -> list:
    """
    Split cleaned text into overlapping chunks.
    """

    if not text:
        return []

    if overlap >= chunk_size:
        raise ValueError("Overlap must be smaller than chunk size.")

    chunks = []

    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size

        chunk_text = text[start:end].strip()

        if chunk_text:
            chunks.append({
                "chunk_id": len(chunks) + 1,
                "text": chunk_text,
                "start": start,
                "end": min(end, text_length)
            })

        start += chunk_size - overlap

    return chunks