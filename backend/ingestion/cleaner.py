import re


def clean_text(text: str) -> str:
    """
    Clean extracted PDF text while preserving meaningful content.
    """

    if not text:
        return ""

    # Normalize line endings
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Remove excessive spaces and tabs
    text = re.sub(r"[ \t]+", " ", text)

    # Remove spaces at the beginning/end of lines
    text = "\n".join(line.strip() for line in text.splitlines())

    # Remove excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def clean_pages(pages: list) -> list:
    """
    Clean text page-by-page while preserving page numbers.
    """

    cleaned_pages = []

    for page in pages:
        cleaned_text = clean_text(page["text"])

        cleaned_pages.append({
            "page": page["page"],
            "text": cleaned_text
        })

    return cleaned_pages