from backend.ingestion.cleaner import clean_text
from backend.ingestion.chunker import create_chunks


sample_text = """
This    is    a sample privacy policy.

We collect name, email address, location
and device information.
"""


cleaned = clean_text(sample_text)

print("CLEANED TEXT:")
print(cleaned)

chunks = create_chunks(
    cleaned,
    chunk_size=10,
    overlap=3
)

print("\nCHUNKS:")

for chunk in chunks:
    print("\n", chunk)