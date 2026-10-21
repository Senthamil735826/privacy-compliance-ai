import sys
from pathlib import Path
from uuid import uuid4
import tempfile

# Ensure both backend directory and project root are on sys.path
_BACKEND_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BACKEND_DIR.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from backend.vector_store.search_service import SemanticSearchService
except ImportError:
    from vector_store.search_service import SemanticSearchService

from ingestion.pdf_parser import extract_text_from_pdf
from ingestion.cleaner import clean_text
from ingestion.chunker import create_chunks
from indicators.indicator_engine import IndicatorEngine


# =========================================================
# INITIALIZE INDICATOR ENGINE
# =========================================================

engine = IndicatorEngine()
semantic_search = SemanticSearchService()


# =========================================================
# INITIALIZE FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title="Privacy Compliance AI",
    description=(
        "Multi-AI Agent Oriented Privacy Policy Compliance "
        "Checking for Mobile IoT Systems"
    ),
    version="0.1.0"
)


# =========================================================
# CORS CONFIGURATION
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://privacy-compliance-ai.vercel.app",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
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

        # STEP 7: Index chunks for semantic search
        document_id = str(uuid4())
        indexed_chunks = 0
        if chunks:
            try:
                indexed_chunks = semantic_search.index_document(document_id, chunks)
            except Exception as index_err:
                print("Semantic indexing error:", repr(index_err))

        # STEP 8: DEBUG INFORMATION
        print("\n" + "=" * 60)
        print("PDF COMPLIANCE ANALYSIS DEBUG")
        print("=" * 60)

        print("Filename:", file.filename)
        print("Document ID:", document_id)
        print("Indexed chunks:", indexed_chunks)
        print("Extracted characters:", len(extracted_text))
        print("Cleaned characters:", len(cleaned_text))
        print("Total pages:", result.get("total_pages"))
        print("Total chunks:", len(chunks))

        print("\nFirst 500 characters of cleaned text:")
        print(cleaned_text[:500])

        # STEP 9: Analyze the complete cleaned document
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

        # STEP 10: Return analysis results
        return {
            "status": "success",

            "document_id": document_id,
            "indexed_chunks": indexed_chunks,

            "document": {
                "document_id": document_id,
                "filename": file.filename,
                "total_pages": result.get("total_pages", 0),
                "total_characters": len(cleaned_text),
                "total_chunks": len(chunks),
                "indexed_chunks": indexed_chunks
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
        # STEP 11: Remove temporary PDF
        if temp_file_path:
            Path(temp_file_path).unlink(missing_ok=True)

        await file.close()


# =========================================================
# SEMANTIC SEARCH ENDPOINT
# =========================================================

class PolicySearchRequest(BaseModel):
    document_id: str = Field(..., min_length=1, description="Unique ID of the uploaded document")
    query: str = Field(..., min_length=1, description="Search query text")
    top_k: int = Field(default=3, ge=1, le=50, description="Maximum number of passages to retrieve")


@app.post("/api/policy/search")
def search_policy(request: PolicySearchRequest):
    """Retrieve relevant policy passages using semantic search on document chunks."""
    clean_doc_id = request.document_id.strip()
    clean_query = request.query.strip()

    if not clean_doc_id:
        raise HTTPException(
            status_code=422,
            detail="document_id cannot be empty or whitespace only."
        )

    if not clean_query:
        raise HTTPException(
            status_code=422,
            detail="query cannot be empty or whitespace only."
        )

    if not semantic_search.has_document(clean_doc_id):
        raise HTTPException(
            status_code=404,
            detail=f"No indexed document found for ID: {clean_doc_id}"
        )

    try:
        results = semantic_search.search(
            document_id=clean_doc_id,
            query=clean_query,
            top_k=request.top_k,
        )

        return {
            "status": "success",
            "document_id": clean_doc_id,
            "query": clean_query,
            "results": results
        }

    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc)
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc)
        ) from exc

    except Exception as exc:
        print("Semantic search error:", repr(exc))
        raise HTTPException(
            status_code=500,
            detail="An error occurred while executing semantic search."
        ) from exc