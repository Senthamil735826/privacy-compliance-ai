from fastapi import FastAPI, UploadFile, File, HTTPException
from pathlib import Path
import tempfile

from ingestion.pdf_parser import extract_text_from_pdf
from ingestion.cleaner import clean_text
from ingestion.chunker import create_chunks
from indicators.indicator_engine import analyze_policy


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
        # ==========================================
        # STEP 1: Extract text from PDF
        # ==========================================

        result = extract_text_from_pdf(temp_file_path)

        # ==========================================
        # STEP 2: Clean extracted text
        # ==========================================

        cleaned_text = clean_text(result["text"])

        # ==========================================
        # STEP 3: Split text into chunks
        # ==========================================

        chunks = create_chunks(
            cleaned_text,
            chunk_size=200,
            overlap=30
        )

        # ==========================================
        # STEP 4: Analyze privacy indicators
        # B1 → B40
        # ==========================================

        indicator_results = analyze_policy(cleaned_text)

        # ==========================================
        # STEP 5: Calculate compliance summary
        # ==========================================

        total_indicators = len(indicator_results)

        matched_indicators = [
            indicator
            for indicator in indicator_results
            if indicator["matched"]
        ]

        not_matched_indicators = [
            indicator
            for indicator in indicator_results
            if not indicator["matched"]
        ]

        matched_count = len(matched_indicators)
        not_matched_count = len(not_matched_indicators)

        coverage = (
            (matched_count / total_indicators) * 100
            if total_indicators > 0
            else 0
        )

        # ==========================================
        # STEP 6: Return complete analysis
        # ==========================================

        return {
            "status": "success",

            "document": {
                "filename": file.filename,
                "total_pages": result["total_pages"],
                "total_characters": len(cleaned_text),
                "total_chunks": len(chunks)
            },

            "compliance_summary": {
                "total_indicators": total_indicators,
                "matched": matched_count,
                "not_matched": not_matched_count,
                "coverage": round(coverage, 2)
            },

            "indicators": indicator_results,

            "chunks": chunks
        }

    finally:
        Path(temp_file_path).unlink(missing_ok=True)