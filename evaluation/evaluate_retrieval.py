import json
import re
import sys
from pathlib import Path

# --------------------------------------------------
# PATH CONFIGURATION
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
QUERIES_FILE = PROJECT_ROOT / "evaluation" / "retrieval_queries.json"
PDF_FILE = PROJECT_ROOT / "dataset" / "sample_privacy_policy.pdf"
REPORT_FILE = PROJECT_ROOT / "evaluation" / "retrieval_evaluation_report.json"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from backend.ingestion.pdf_parser import extract_text_from_pdf
from backend.ingestion.cleaner import clean_text
from backend.ingestion.chunker import create_chunks
from backend.vector_store.search_service import SemanticSearchService


def normalize_for_matching(text: str) -> str:
    """Normalize whitespace and lowercase for reliable phrase matching."""
    return re.sub(r"\s+", " ", text).strip().lower()


def check_chunk_relevance(chunk_text: str, key_phrases: list[str]) -> bool:
    """Check if any of the expected key phrases appear in the chunk text."""
    normalized_chunk = normalize_for_matching(chunk_text)
    for phrase in key_phrases:
        if normalize_for_matching(phrase) in normalized_chunk:
            return True
    return False


def main():
    if not PDF_FILE.is_file():
        raise FileNotFoundError(f"Sample PDF not found at: {PDF_FILE}")

    if not QUERIES_FILE.is_file():
        raise FileNotFoundError(f"Queries file not found at: {QUERIES_FILE}")

    with QUERIES_FILE.open("r", encoding="utf-8") as f:
        query_data = json.load(f)

    queries = query_data.get("queries", [])
    if not queries:
        raise ValueError("No queries found in evaluation dataset.")

    # 1. Ingest, clean, and chunk the sample policy
    extraction_result = extract_text_from_pdf(str(PDF_FILE))
    raw_text = extraction_result.get("text", "")
    if not raw_text.strip():
        raise ValueError("Failed to extract readable text from sample PDF.")

    cleaned_text = clean_text(raw_text)
    chunks = create_chunks(cleaned_text, chunk_size=200, overlap=30)
    if not chunks:
        raise ValueError("Failed to produce chunks from sample PDF.")

    # 2. Build a fresh in-memory FAISS index
    search_service = SemanticSearchService()
    document_id = "eval-sample-policy"
    indexed_count = search_service.index_document(document_id, chunks)

    # 3. Execute all queries with top_k = 3
    query_results = []
    successful_queries = 0
    top_k = 3

    for item in queries:
        qid = item["query_id"]
        topic = item["topic"]
        query_text = item["query"]
        key_phrases = item.get("key_phrases", [])

        search_output = search_service.search(
            document_id=document_id,
            query=query_text,
            top_k=top_k,
        )

        relevant_found = False
        first_relevant_rank = None
        retrieved_details = []

        for rank, res in enumerate(search_output, start=1):
            is_relevant = check_chunk_relevance(res["text"], key_phrases)
            if is_relevant and not relevant_found:
                relevant_found = True
                first_relevant_rank = rank

            retrieved_details.append({
                "rank": rank,
                "chunk_id": res.get("chunk_id"),
                "similarity": round(float(res.get("similarity", 0.0)), 4),
                "is_relevant": is_relevant,
                "text_snippet": res["text"][:120] + "..." if len(res["text"]) > 120 else res["text"],
            })

        if relevant_found:
            successful_queries += 1

        query_results.append({
            "query_id": qid,
            "topic": topic,
            "query": query_text,
            "success": relevant_found,
            "first_relevant_rank": first_relevant_rank,
            "highest_similarity": retrieved_details[0]["similarity"] if retrieved_details else None,
            "retrieved_results": retrieved_details,
        })

    # 4. Calculate Recall@3
    total_queries = len(queries)
    recall_at_3 = (successful_queries / total_queries) * 100.0 if total_queries else 0.0

    report = {
        "dataset_schema_version": query_data.get("schema_version", "1.0"),
        "document": str(PDF_FILE.name),
        "total_chunks_indexed": indexed_count,
        "total_queries": total_queries,
        "successful_queries": successful_queries,
        "failed_queries": total_queries - successful_queries,
        "top_k": top_k,
        "recall_at_3": round(recall_at_3, 2),
        "results": query_results,
    }

    # 5. Save results to retrieval_evaluation_report.json
    with REPORT_FILE.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # --------------------------------------------------
    # CONSOLE SUMMARY
    # --------------------------------------------------
    print("=" * 80)
    print("PRIVACY COMPLIANCE AI — SEMANTIC SEARCH RETRIEVAL EVALUATION")
    print("=" * 80)
    print(f"Sample Document:       {PDF_FILE.name}")
    print(f"Chunks Indexed:        {indexed_count}")
    print(f"Total Queries:         {total_queries}")
    print(f"Top-k Depth:           {top_k}")
    print("-" * 80)
    print(f"{'ID':<10}{'Topic':<22}{'Top Sim':>9}{'Best Rank':>12}{'Success':>10}")
    print("-" * 80)

    for r in query_results:
        rank_str = str(r["first_relevant_rank"]) if r["first_relevant_rank"] is not None else "None"
        success_str = "YES" if r["success"] else "NO"
        sim_str = f"{r['highest_similarity']:.4f}" if r["highest_similarity"] is not None else "N/A"
        print(f"{r['query_id']:<10}{r['topic']:<22}{sim_str:>9}{rank_str:>12}{success_str:>10}")

    print("=" * 80)
    print(f"OVERALL RECALL@{top_k}: {recall_at_3:.2f}% ({successful_queries}/{total_queries} queries succeeded)")
    print(f"Report saved to: {REPORT_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    main()
