from pypdf import PdfReader


def extract_text_from_pdf(file_path: str) -> dict:
    reader = PdfReader(file_path)

    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""

        pages.append({
            "page": page_number,
            "text": text
        })

    full_text = "\n\n".join(page["text"] for page in pages)

    return {
        "total_pages": len(reader.pages),
        "total_characters": len(full_text),
        "text": full_text,
        "pages": pages
    }