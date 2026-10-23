import io
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.main import app, semantic_search


@pytest.fixture
def client():
    return TestClient(app)


def create_minimal_pdf_bytes(text: str) -> bytes:
    """Construct a minimal valid PDF containing the specified text string."""
    escaped_text = text.replace("(", "\\(").replace(")", "\\)")
    stream_content = f"BT /F1 12 Tf 72 712 Td ({escaped_text}) Tj ET\n"
    stream_len = len(stream_content.encode("latin1"))

    pdf = (
        f"%PDF-1.4\n"
        f"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        f"2 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        f"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
        f"4 0 obj << /Length {stream_len} >> stream\n"
        f"{stream_content}"
        f"endstream endobj\n"
        f"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        f"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n"
        f"0000000115 00000 n \n0000000244 00000 n \n0000000367 00000 n \n"
        f"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n439\n%%EOF"
    )
    return pdf.encode("latin1")


# ============================================================================
# 1. GENERAL API ENDPOINT TESTS
# ============================================================================

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


def test_health_check_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["project"] == "Privacy Compliance AI"
    assert "version" in data


# ============================================================================
# 2. PDF UPLOAD AND INDEXING ENDPOINT TESTS
# ============================================================================

def test_upload_policy_non_pdf_rejected(client):
    response = client.post(
        "/api/policy/upload",
        files={"file": ("notes.txt", io.BytesIO(b"Hello world"), "text/plain")},
    )
    assert response.status_code == 400
    assert "Only PDF files are allowed" in response.json()["detail"]


def test_upload_policy_empty_file_rejected(client):
    response = client.post(
        "/api/policy/upload",
        files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
    )
    assert response.status_code == 400
    assert "The uploaded PDF is empty" in response.json()["detail"]


def test_upload_policy_unreadable_pdf_rejected(client):
    # Valid PDF syntax with an empty page and no text content stream
    pdf_no_text = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >> endobj\n"
        b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"
        b"trailer << /Size 4 /Root 1 0 R >>\nstartxref\n180\n%%EOF"
    )
    response = client.post(
        "/api/policy/upload",
        files={"file": ("blank.pdf", io.BytesIO(pdf_no_text), "application/pdf")},
    )
    assert response.status_code == 422
    assert "No readable text" in response.json()["detail"]


def test_upload_policy_success_and_indexing(client):
    pdf_bytes = create_minimal_pdf_bytes(
        "Privacy Policy. Contact us at privacy@example.com. "
        "We retain personal data only as long as necessary for business operations."
    )
    response = client.post(
        "/api/policy/upload",
        files={"file": ("privacy_sample.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert response.status_code == 200
    data = response.json()

    # Core required response fields
    assert data["status"] == "success"
    assert "document_id" in data
    assert isinstance(data["document_id"], str)
    assert len(data["document_id"]) > 0

    assert "indexed_chunks" in data
    assert isinstance(data["indexed_chunks"], int)
    assert data["indexed_chunks"] >= 1

    # Preserved sections
    assert "document" in data
    assert "compliance_summary" in data
    assert "indicators" in data
    assert "chunks" in data

    # Document section metadata
    doc = data["document"]
    assert doc["document_id"] == data["document_id"]
    assert doc["indexed_chunks"] == data["indexed_chunks"]
    assert doc["filename"] == "privacy_sample.pdf"
    assert doc["total_pages"] >= 1

    # Verify that the document is actively indexed in the semantic search service
    doc_id = data["document_id"]
    assert semantic_search.has_document(doc_id)

    # Perform semantic search on the uploaded document
    search_res = client.post(
        "/api/policy/search",
        json={
            "document_id": doc_id,
            "query": "How long do you retain personal data?",
            "top_k": 2,
        },
    )
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["status"] == "success"
    assert search_data["document_id"] == doc_id
    assert len(search_data["results"]) >= 1

    top_result = search_data["results"][0]
    assert "text" in top_result
    assert "similarity" in top_result
    assert isinstance(top_result["similarity"], float)
    assert -1.0 <= top_result["similarity"] <= 1.0


# ============================================================================
# 3. SEMANTIC SEARCH ENDPOINT VALIDATION TESTS
# ============================================================================

def test_search_unknown_document_id(client):
    response = client.post(
        "/api/policy/search",
        json={
            "document_id": "nonexistent-doc-id-12345",
            "query": "Where is my data stored?",
            "top_k": 3,
        },
    )
    assert response.status_code == 404
    assert "No indexed document found" in response.json()["detail"]


def test_search_empty_query(client):
    response = client.post(
        "/api/policy/search",
        json={
            "document_id": "some-id",
            "query": "   ",
            "top_k": 3,
        },
    )
    assert response.status_code == 422


def test_search_empty_document_id(client):
    response = client.post(
        "/api/policy/search",
        json={
            "document_id": "   ",
            "query": "Valid query text",
            "top_k": 3,
        },
    )
    assert response.status_code == 422


def test_search_invalid_top_k(client):
    # top_k = 0 rejected (ge=1)
    res0 = client.post(
        "/api/policy/search",
        json={"document_id": "some-id", "query": "query", "top_k": 0},
    )
    assert res0.status_code == 422

    # top_k = -5 rejected
    res_neg = client.post(
        "/api/policy/search",
        json={"document_id": "some-id", "query": "query", "top_k": -5},
    )
    assert res_neg.status_code == 422

    # top_k > 50 rejected (le=50)
    res_high = client.post(
        "/api/policy/search",
        json={"document_id": "some-id", "query": "query", "top_k": 100},
    )
    assert res_high.status_code == 422


def test_multi_document_search_isolation(client):
    # Upload Document 1: Health and medical data policy
    pdf1 = create_minimal_pdf_bytes(
        "Health Clinic Privacy Policy. We collect patient blood pressure, "
        "medical diagnosis records, and lab results for clinical care."
    )
    res1 = client.post(
        "/api/policy/upload",
        files={"file": ("health_policy.pdf", io.BytesIO(pdf1), "application/pdf")},
    )
    assert res1.status_code == 200
    doc1_id = res1.json()["document_id"]

    # Upload Document 2: Gaming and virtual tokens policy
    pdf2 = create_minimal_pdf_bytes(
        "Online Gaming Terms. We record avatar purchases, gaming scores, "
        "and virtual tournament leaderboards."
    )
    res2 = client.post(
        "/api/policy/upload",
        files={"file": ("gaming_policy.pdf", io.BytesIO(pdf2), "application/pdf")},
    )
    assert res2.status_code == 200
    doc2_id = res2.json()["document_id"]

    assert doc1_id != doc2_id

    # Query Document 1 for gaming
    search1 = client.post(
        "/api/policy/search",
        json={"document_id": doc1_id, "query": "virtual tokens and avatars", "top_k": 3},
    )
    assert search1.status_code == 200
    for result in search1.json()["results"]:
        # Must only contain text from Document 1, never Document 2
        assert "avatar" not in result["text"].lower()
        assert "gaming" not in result["text"].lower()

    # Query Document 2 for medical
    search2 = client.post(
        "/api/policy/search",
        json={"document_id": doc2_id, "query": "patient diagnosis and lab tests", "top_k": 3},
    )
    assert search2.status_code == 200
    for result in search2.json()["results"]:
        # Must only contain text from Document 2, never Document 1
        assert "blood pressure" not in result["text"].lower()
        assert "clinical" not in result["text"].lower()


def test_agents_status_endpoint(client):
    response = client.get("/api/agents/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "providers" in data
    assert "gemini" in data["providers"]
    assert "groq" in data["providers"]
    assert "claude" in data["providers"]
    assert "openai" in data["providers"]
    assert "deepseek" in data["providers"]
    assert "openrouter" in data["providers"]
    for p in ["gemini", "groq", "claude", "openai", "deepseek", "openrouter"]:
        prov = data["providers"][p]
        assert "status" in prov
        assert "status_label" in prov
        assert "is_available" in prov
        assert "model" in prov
        assert "configured" in prov



def test_agents_check_endpoint(client):
    response = client.post("/api/agents/check", json={"provider": "groq"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "provider" in data
    assert data["provider"]["provider"] == "groq"


def test_agents_evaluate_endpoint(client):
    from unittest.mock import patch
    from backend.agents.mock_evaluator import MockPrivacyEvaluator

    mock_evals = [
        MockPrivacyEvaluator("sim-1"),
        MockPrivacyEvaluator("sim-2"),
    ]
    with patch("backend.agents.provider_health.global_health_service.get_available_evaluators", return_value=mock_evals):
        response = client.post(
            "/api/agents/evaluate",
            json={
                "primary_indicator_id": "A1",
                "indicator_id": "B1",
                "indicator_description": "Privacy policy title",
                "evidence": "Policy Title: Privacy Policy 2026.",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "result" in data
        assert "aggregation" in data["result"]
        assert "evaluations" in data["result"]


