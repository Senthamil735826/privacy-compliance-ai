from fastapi import FastAPI, UploadFile, File, HTTPException
from pathlib import Path
import tempfile

from ingestion.pdf_parser import extract_text_from_pdf
from ingestion.cleaner import clean_text
from ingestion.chunker import create_chunks
from indicators.indicator_engine import IndicatorEngine


# Initialize indicator engine
engine = IndicatorEngine()


# Initialize FastAPI application
app = FastAPI(
    title="Privacy Compliance AI",
    description=(
        "Multi-AI Agent Oriented Privacy Policy Compliance "
        "Checking for Mobile IoT Systems"
    ),
    version="0.1.0"
)


# =========================================================
# ROOT ENDPOINT
# =========================================================

@app.get("/")
def read_root():
    return {
        "message": (
            "Welcome to Privacy Compliance AI API. "
            "Visit /docs for the API documentation."
        )
    }


# =========================================================
# HEALTH CHECK ENDPOINT
# =========================================================

@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "project": "Privacy Compliance AI",
        "version": "0.1.0"
    }


# =========================================================
# PDF UPLOAD AND COMPLIANCE ANALYSIS
# =========================================================

@app.post("/api/policy/upload")
async def upload_policy(file: UploadFile = File(...)):

    # STEP 1: Validate uploaded file
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed."
        )

    if file.content_type not in (
        "application/pdf",
        "application/octet-stream"
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid file content type. Please upload a PDF."
        )

    temp_file_path = None

    try:
        # STEP 2: Read uploaded PDF
        file_content = await file.read()

        if not file_content:
            raise HTTPException(
                status_code=400,
                detail="The uploaded PDF is empty."
            )

        # STEP 3: Save PDF temporarily
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".pdf"
        ) as temp_file:

            temp_file.write(file_content)
            temp_file_path = temp_file.name

        # STEP 4: Extract text from PDF
        result = extract_text_from_pdf(temp_file_path)

        extracted_text = result.get("text", "")

        if not extracted_text or not extracted_text.strip():
            raise HTTPException(
                status_code=422,
                detail=(
                    "No readable text was extracted from the PDF. "
                    "Please upload a text-based PDF."
                )
            )

        # STEP 5: Clean extracted text
        cleaned_text = clean_text(extracted_text)

        # STEP 6: Create overlapping text chunks
        chunks = create_chunks(
            cleaned_text,
            chunk_size=200,
            overlap=30
        )

        # STEP 7: DEBUG INFORMATION
        # These logs help us investigate the coverage mismatch.
        print("\n" + "=" * 60)
        print("PDF COMPLIANCE ANALYSIS DEBUG")
        print("=" * 60)

        print("Filename:", file.filename)
        print("Extracted characters:", len(extracted_text))
        print("Cleaned characters:", len(cleaned_text))
        print("Total pages:", result.get("total_pages"))
        print("Total chunks:", len(chunks))

        print("\nFirst 500 characters of cleaned text:")
        print(cleaned_text[:500])

        # STEP 8: Analyze the complete cleaned document
        analysis = engine.analyze_policy(cleaned_text)

        print("\nIndicator analysis results:")
        print("Total indicators:", analysis["total_indicators"])
        print("Found:", analysis["found"])
        print("Not found:", analysis["not_found"])
        print("Coverage:", analysis["coverage"])

        # Print every matched indicator for debugging
        print("\nMatched indicator IDs:")

        matched_indicators = [
            item["id"]
            for item in analysis["results"]
            if item.get("matched", False)
        ]

        print(matched_indicators)
        print("=" * 60 + "\n")

        # STEP 9: Return analysis results
        return {
            "status": "success",

            "document": {
                "filename": file.filename,
                "total_pages": result.get("total_pages", 0),
                "total_characters": len(cleaned_text),
                "total_chunks": len(chunks)
            },

            "compliance_summary": {
                "total_indicators": analysis["total_indicators"],
                "matched": analysis["found"],
                "not_matched": analysis["not_found"],
                "coverage": analysis["coverage"]
            },

            "indicators": analysis["results"],

            "chunks": chunks
        }

    except HTTPException:
        # Preserve intentional HTTP errors
        raise

    except Exception as exc:
        # Log the error for debugging
        print("PDF analysis error:", repr(exc))

        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing the PDF."
        ) from exc

    finally:
        # STEP 10: Remove temporary PDF
        if temp_file_path:
            Path(temp_file_path).unlink(missing_ok=True)

        await file.close()