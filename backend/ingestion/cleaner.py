import re


def clean_text(text: str) -> str:
    """
    Clean extracted PDF text before chunking.
    """

    # Normalize line breaks
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Remove excessive spaces
    text = re.sub(r"[ \t]+", " ", text)

    # Remove excessive blank lines
    text = re.sub(r"\n\s*\n+", "\n\n", text)

    # Remove spaces at beginning/end of lines
    text = "\n".join(line.strip() for line in text.splitlines())

    # Final cleanup
    text = text.strip()

    return text