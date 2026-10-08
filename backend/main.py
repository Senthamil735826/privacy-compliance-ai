from fastapi import FastAPI, UploadFile, File, HTTPException
from pathlib import Path
import tempfile

from ingestion.pdf_parser import extract_text_from_pdf
from ingestion.cleaner import clean_text
from ingestion.chunker import create_chunks


app = FastAPI(
    title="Privacy Compliance AI",
    description="Multi-AI Agent Oriented Privacy Policy Compliance Checking for Mobile IoT Systems",
    version="0.1.0"
)


@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "project": "Privacy Compliance AI",
        "version": "0.1.0"
    }


@app.post("/api/policy/upload")
async def upload_policy(file: UploadFile = File(...)):

    # Check file type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed."
        )

    # Read uploaded file
    file_content = await file.read()

    # Save temporarily
    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".pdf"
    ) as temp_file:

        temp_file.write(file_content)
        temp_file_path = temp_file.name

    try:
        # Step 1: Extract text from PDF
        result = extract_text_from_pdf(temp_file_path)

        # Step 2: Clean extracted text
        cleaned_text = clean_text(result["text"])

        # Step 3: Split into chunks
        chunks = create_chunks(
            cleaned_text,
            chunk_size=200,
            overlap=30
        )

        return {
            "status": "success",
            "filename": file.filename,
            "total_pages": result["total_pages"],
            "total_characters": len(cleaned_text),
            "total_chunks": len(chunks),
            "text": cleaned_text,
            "chunks": chunks
        }

    finally:
        Path(temp_file_path).unlink(missing_ok=True)