"""
Unit and integration tests for Phase 1 - Automated TCAM Metric Calculation.

Validates:
1. Benchmark-calibrated Inherent Difficulty (H)
2. Evidence Recall / Coverage Proxy (R) without conflating max cosine with recall
3. Evidence Dispersion (D) across chunks and pages
4. Semantic Ambiguity (A) from similarity flatness, hedging, and contradictions
5. High-confidence explicit evidence (theta < 0.4 -> 1 evaluator)
6. Scattered evidence across document chunks (0.4 <= theta < 0.7 -> 3 evaluators)
7. Ambiguous evidence with flat similarities and hedges (theta >= 0.7 -> 5 evaluators)
8. Missing evidence (R=0, A=1 -> maximum scarcity)
9. Conflicting evidence (contradiction signals)
10. Strict boundary conditions at exactly theta = 0.40 and theta = 0.70
"""

import pytest

from backend.agents.tcam_metrics import (
    CALIBRATED_INHERENT_DIFFICULTY,
    compute_automated_tcam_metrics,
    calculate_evidence_recall_proxy,
    calculate_evidence_dispersion,
    calculate_semantic_ambiguity,
    get_calibrated_inherent_difficulty,
)
from backend.agents.tcam_router import TCAMConfig, TCAMRouter, TCAMResult
from backend.agents.agent_pipeline import PrivacyAgentPipeline
from backend.agents.dynamic_scheduler import DynamicScheduler
from backend.agents.mock_evaluator import MockPrivacyEvaluator


# ============================================================================
# 1. BENCHMARK CALIBRATED INHERENT DIFFICULTY
# ============================================================================

def test_calibrated_inherent_difficulty_known_indicators():
    """Verify calibrated empirical benchmark scores for statutory indicators."""
    h_b1, r_b1 = get_calibrated_inherent_difficulty("B1", "A1")
    assert h_b1 == 0.15
    assert "B1" in r_b1

    h_b7, r_b7 = get_calibrated_inherent_difficulty("B7", "A2")
    assert h_b7 == 0.40

    h_b13, r_b13 = get_calibrated_inherent_difficulty("B13", "A3")
    assert h_b13 == 0.75

    h_b15, r_b15 = get_calibrated_inherent_difficulty("B15", "A3")
    assert h_b15 == 0.80

    h_b37, r_b37 = get_calibrated_inherent_difficulty("B37", "A7")
    assert h_b37 == 0.80


def test_calibrated_inherent_difficulty_fallback():
    """Verify category fallback for unlisted secondary indicators."""
    h_fallback, r_fallback = get_calibrated_inherent_difficulty("B99", "A3")
    assert h_fallback == 0.70  # A3 category default
    assert "fallback" in r_fallback.lower()


# ============================================================================
# 2. EVIDENCE RECALL / COVERAGE PROXY (NO MAX COSINE CONFLATION)
# ============================================================================

def test_recall_proxy_does_not_equate_max_cosine_similarity():
    """
    Mathematical requirement: Max cosine similarity must NOT be equated to true recall.
    A single chunk with high similarity (0.95) but lacking statutory concept coverage
    must NOT produce recall R = 0.95.
    """
    indicator_desc = (
        "Specifies exact retention periods, storage schedules, and permanent deletion "
        "procedures for inactive customer accounts."
    )
    # Evidence has high similarity from generic words, but misses statutory retention concepts
    high_sim_irrelevant_chunks = [
        {"chunk_id": 1, "text": "Customer accounts are maintained in our database.", "similarity": 0.95}
    ]
    evidence_text = "Customer accounts are maintained in our database."

    recall, lex_cov, sem_dens, rationale = calculate_evidence_recall_proxy(
        evidence_text=evidence_text,
        indicator_description=indicator_desc,
        retrieved_chunks=high_sim_irrelevant_chunks,
    )

    # Max similarity is 0.95, but recall proxy must reflect low lexical coverage of required concepts
    assert recall < 0.80
    assert recall != 0.95
    assert lex_cov < 0.50
    assert "Coverage proxy" in rationale


def test_recall_proxy_empty_evidence():
    """Empty evidence text must produce recall R = 0.0."""
    recall, lex_cov, sem_dens, rationale = calculate_evidence_recall_proxy(
        evidence_text="",
        indicator_description="Specifies retention period",
    )
    assert recall == 0.0
    assert lex_cov == 0.0
    assert sem_dens == 0.0


# ============================================================================
# 3. EVIDENCE DISPERSION ACROSS CHUNKS AND PAGES
# ============================================================================

def test_evidence_dispersion_single_chunk():
    """Evidence confined to a single chunk must have zero dispersion D = 0.0."""
    chunks = [{"chunk_id": 3, "similarity": 0.78}]
    dispersion, span, chunk_ids, rationale = calculate_evidence_dispersion(
        evidence_text="Single chunk text",
        retrieved_chunks=chunks,
        total_document_chunks=50,
    )
    assert dispersion == 0.0
    assert span == 0.0
    assert chunk_ids == [3]


def test_evidence_dispersion_scattered_chunks():
    """Evidence scattered from beginning to end of document has high dispersion."""
    # Chunks spread from index 2 to index 48 in a 50-chunk document (92% span)
    scattered_chunks = [
        {"chunk_id": 2, "similarity": 0.65},
        {"chunk_id": 24, "similarity": 0.60},
        {"chunk_id": 48, "similarity": 0.70},
    ]
    dispersion, span, chunk_ids, rationale = calculate_evidence_dispersion(
        evidence_text="Scattered text",
        retrieved_chunks=scattered_chunks,
        total_document_chunks=50,
    )
    assert span > 0.80
    assert dispersion > 0.60
    assert chunk_ids == [2, 24, 48]
    assert "scattered" in rationale.lower()


# ============================================================================
# 4. SEMANTIC AMBIGUITY (SIMILARITY FLATNESS, HEDGING, CONTRADICTIONS)
# ============================================================================

def test_semantic_ambiguity_decisive_vs_flat_distribution():
    """A decisive margin between top candidates lowers ambiguity compared to flat candidates."""
    # Decisive retrieval: top=0.90, second=0.60 (margin = 0.30 >= 0.20 threshold)
    decisive_chunks = [
        {"chunk_id": 1, "similarity": 0.90},
        {"chunk_id": 2, "similarity": 0.60},
    ]
    amb_decisive, sim_amb_decisive, _, _ = calculate_semantic_ambiguity(
        evidence_text="We permanently erase all user records after 30 days.",
        retrieved_chunks=decisive_chunks,
    )

    # Flat retrieval: top=0.55, second=0.54 (margin = 0.01)
    flat_chunks = [
        {"chunk_id": 1, "similarity": 0.55},
        {"chunk_id": 2, "similarity": 0.54},
    ]
    amb_flat, sim_amb_flat, _, _ = calculate_semantic_ambiguity(
        evidence_text="We permanently erase all user records after 30 days.",
        retrieved_chunks=flat_chunks,
    )

    assert sim_amb_flat > sim_amb_decisive
    assert amb_flat > amb_decisive


def test_semantic_ambiguity_hedging_and_contradictions():
    """Linguistic hedges and contradictions directly increase ambiguity."""
    clean_text = "We delete your personal data within 14 business days upon verified request."
    amb_clean, _, hedge_clean, _ = calculate_semantic_ambiguity(evidence_text=clean_text)

    hedged_and_conflicted = (
        "We do not sell personal data. However, we may from time to time share, disclose, or sell "
        "identifiers at our discretion where applicable and as reasonably necessary."
    )
    amb_hedged, _, hedge_hedged, rationale = calculate_semantic_ambiguity(
        evidence_text=hedged_and_conflicted
    )

    assert hedge_hedged > hedge_clean
    assert amb_hedged > amb_clean
    assert "contradiction: detected" in rationale.lower()


# ============================================================================
# 5. HIGH-CONFIDENCE EXPLICIT EVIDENCE (THETA < 0.4 -> 1 EVALUATOR)
# ============================================================================

def test_high_confidence_explicit_evidence_routes_to_single_evaluator():
    """
    Clear, explicit metadata with high coverage, concentrated in 1 chunk,
    unambiguous language -> theta < 0.40 -> 1 evaluator.
    """
    # B1: Inherent difficulty = 0.15
    explanation = compute_automated_tcam_metrics(
        indicator_id="B1",
        indicator_description="Specifies privacy policy name and legal document title.",
        primary_indicator_id="A1",
        evidence_text="Privacy Policy and Master Terms of Service Document Title.",
        retrieved_chunks=[
            {"chunk_id": 0, "similarity": 0.88},
            {"chunk_id": 1, "similarity": 0.50},
        ],
        total_document_chunks=20,
    )

    assert explanation.inherent_difficulty == 0.15
    assert explanation.evidence_recall >= 0.60
    assert explanation.evidence_dispersion <= 0.10  # Concentrated in adjacent chunks
    assert explanation.complexity_score < 0.40
    assert explanation.routing_decision == 1
    assert explanation.complexity_level == "low"


# ============================================================================
# 6. SCATTERED EVIDENCE (0.40 <= THETA < 0.70 -> 3 EVALUATORS)
# ============================================================================

def test_scattered_evidence_routes_to_three_evaluators():
    """
    Moderate difficulty indicator (B7, H=0.40) with evidence dispersed across chunks
    spread across 80% of document -> theta in [0.40, 0.70) -> 3 evaluators.
    """
    explanation = compute_automated_tcam_metrics(
        indicator_id="B7",
        indicator_description="Identifies user account credentials and registration data.",
        primary_indicator_id="A2",
        evidence_text="User registration email. Account credentials. Profile settings.",
        retrieved_chunks=[
            {"chunk_id": 2, "similarity": 0.60},
            {"chunk_id": 18, "similarity": 0.58},
            {"chunk_id": 35, "similarity": 0.62},
        ],
        total_document_chunks=40,
    )

    assert explanation.inherent_difficulty == 0.40
    assert explanation.evidence_dispersion >= 0.50
    assert 0.40 <= explanation.complexity_score < 0.70
    assert explanation.routing_decision == 3
    assert explanation.complexity_level == "medium"


# ============================================================================
# 7. AMBIGUOUS EVIDENCE (THETA >= 0.70 -> 5 EVALUATORS)
# ============================================================================

def test_ambiguous_evidence_routes_to_five_evaluators():
    """
    High-difficulty indicator (B15 Cross-border, H=0.80) with ambiguous hedges and flat retrieval
    -> theta >= 0.70 -> 5 evaluators.
    """
    explanation = compute_automated_tcam_metrics(
        indicator_id="B15",
        indicator_description="Specifies cross-border data transfer mechanisms, adequacy decisions, and standard contractual clauses.",
        primary_indicator_id="A3",
        evidence_text=(
            "Data may be transferred overseas from time to time to third parties at our discretion "
            "where applicable and to the extent permitted by local law."
        ),
        retrieved_chunks=[
            {"chunk_id": 5, "similarity": 0.42},
            {"chunk_id": 6, "similarity": 0.41},
            {"chunk_id": 7, "similarity": 0.40},
        ],
        total_document_chunks=30,
    )

    assert explanation.inherent_difficulty == 0.80
    assert explanation.semantic_ambiguity >= 0.50
    assert explanation.complexity_score >= 0.70
    assert explanation.routing_decision == 5
    assert explanation.complexity_level == "high"


# ============================================================================
# 8. MISSING EVIDENCE
# ============================================================================

def test_missing_evidence_maximizes_scarcity():
    """Empty evidence text maximizes evidence scarcity and elevates complexity."""
    explanation = compute_automated_tcam_metrics(
        indicator_id="B13",
        indicator_description="Legal basis for data processing.",
        primary_indicator_id="A3",
        evidence_text="",
        retrieved_chunks=[],
    )

    assert explanation.evidence_recall == 0.0
    assert explanation.semantic_ambiguity == 1.0
    # S = 1 - [1/3*0 + 1/3*(1-0) + 1/3*(1-1)] = 1 - 1/3 = 2/3 = 0.6667
    assert explanation.evidence_scarcity >= 0.66
    assert explanation.complexity_score >= 0.70
    assert explanation.routing_decision == 5


# ============================================================================
# 9. CONFLICTING EVIDENCE
# ============================================================================

def test_conflicting_evidence_heightens_ambiguity():
    """Contradiction between assertion and denial increases ambiguity and raises complexity."""
    conflicting_text = (
        "We do not sell your personal data. We may sell customer identifiers to select advertising "
        "partners from time to time as permitted by law."
    )
    explanation = compute_automated_tcam_metrics(
        indicator_id="B26",
        indicator_description="Sale of Personal Information disclosures.",
        primary_indicator_id="A5",
        evidence_text=conflicting_text,
    )

    assert explanation.semantic_ambiguity >= 0.50
    assert "contradiction: detected" in explanation.semantic_ambiguity_rationale.lower()


# ============================================================================
# 10. BOUNDARY CONDITIONS AT EXACTLY THETA = 0.40 AND THETA = 0.70
# ============================================================================

def test_boundary_condition_at_0_40():
    """
    Test exact boundary at theta = 0.40:
    theta < 0.40 -> 1 evaluator
    theta >= 0.40 -> 3 evaluators
    """
    router = TCAMRouter()

    # Just below 0.40: H=0.30, S=0.49 -> theta = 0.5*0.30 + 0.5*0.49 = 0.395 < 0.40
    # To get S = 0.49: 1 - [1/3*R + 1/3*(1-D) + 1/3*(1-A)] = 0.49
    # -> 1/3*(R + 1-D + 1-A) = 0.51 -> sum = 1.53
    # Let R=0.53, D=0.0, A=0.0 -> sum = 0.53 + 1.0 + 1.0 = 2.53 (S = 1 - 2.53/3 = 0.156)
    # Using direct values:
    res_below = router.route(
        primary_indicator_id="A1",
        inherent_difficulty=0.38,
        evidence_recall=1.0,
        evidence_dispersion=0.0,
        semantic_ambiguity=0.0,
    )
    # S = 1 - [1/3 + 1/3 + 1/3] = 0.0 -> theta = 0.5*0.38 + 0 = 0.19 < 0.40
    assert res_below.evaluator_count == 1
    assert res_below.complexity_level == "low"

    # Exactly at boundary 0.40:
    # If H = 0.40 and S = 0.40 -> theta = 0.4000 -> 3 evaluators
    # To get S = 0.40: 1/3*(R + 1-D + 1-A) = 0.60 -> R + 1-D + 1-A = 1.80
    # Let R=0.80, D=0.50, A=0.50 -> 0.80 + 0.50 + 0.50 = 1.80 -> S = 0.40
    res_at_040 = router.route(
        primary_indicator_id="A2",
        inherent_difficulty=0.40,
        evidence_recall=0.80,
        evidence_dispersion=0.50,
        semantic_ambiguity=0.50,
    )
    assert round(res_at_040.complexity_score, 4) == 0.4000
    assert res_at_040.evaluator_count == 3
    assert res_at_040.complexity_level == "medium"


def test_boundary_condition_at_0_70():
    """
    Test exact boundary at theta = 0.70:
    theta < 0.70 -> 3 evaluators
    theta >= 0.70 -> 5 evaluators
    """
    router = TCAMRouter()

    # Just below 0.70:
    # H = 0.68, S = 0.70 -> theta = 0.5*0.68 + 0.5*0.70 = 0.69 < 0.70 -> 3 evaluators
    # To get S = 0.70: R + 1-D + 1-A = 0.90 -> Let R=0.30, D=0.70, A=0.70 -> 0.30 + 0.30 + 0.30 = 0.90 -> S = 0.70
    res_below_070 = router.route(
        primary_indicator_id="A3",
        inherent_difficulty=0.68,
        evidence_recall=0.30,
        evidence_dispersion=0.70,
        semantic_ambiguity=0.70,
    )
    assert res_below_070.complexity_score < 0.70
    assert res_below_070.evaluator_count == 3
    assert res_below_070.complexity_level == "medium"

    # Exactly at boundary 0.70:
    # H = 0.70, S = 0.70 -> theta = 0.7000 -> 5 evaluators
    res_at_070 = router.route(
        primary_indicator_id="A3",
        inherent_difficulty=0.70,
        evidence_recall=0.30,
        evidence_dispersion=0.70,
        semantic_ambiguity=0.70,
    )
    assert round(res_at_070.complexity_score, 4) == 0.7000
    assert res_at_070.evaluator_count == 5
    assert res_at_070.complexity_level == "high"


# ============================================================================
# 11. END-TO-END PIPELINE INTEGRATION
# ============================================================================

def test_pipeline_integration_with_automated_explanation():
    """Ensure PrivacyAgentPipeline preserves explanation and chunk metadata."""
    evaluators = [
        MockPrivacyEvaluator("TestAgent-1"),
        MockPrivacyEvaluator("TestAgent-2"),
        MockPrivacyEvaluator("TestAgent-3"),
    ]
    pipeline = PrivacyAgentPipeline(
        router=TCAMRouter(),
        scheduler=DynamicScheduler(),
        evaluators=evaluators,
    )

    explanation = compute_automated_tcam_metrics(
        indicator_id="B7",
        indicator_description="Collects account identifiers.",
        primary_indicator_id="A2",
        evidence_text="User accounts require email and username.",
        retrieved_chunks=[{"chunk_id": 4, "similarity": 0.82}],
    )

    result = pipeline.evaluate_indicator(
        primary_indicator_id="A2",
        indicator_id="B7",
        indicator_description="Collects account identifiers.",
        evidence="User accounts require email and username.",
        inherent_difficulty=explanation.inherent_difficulty,
        evidence_recall=explanation.evidence_recall,
        evidence_dispersion=explanation.evidence_dispersion,
        semantic_ambiguity=explanation.semantic_ambiguity,
        explanation=explanation.to_dict(),
        referenced_chunks=explanation.referenced_chunks,
    )

    assert "tcam" in result
    assert "tcam_explanation" in result
    assert result["tcam_explanation"]["inherent_difficulty"] == explanation.inherent_difficulty
    assert result["tcam"]["referenced_chunks"] == [4]
    assert result["aggregation"]["final_decision"] in ("compliant", "non_compliant", "inconclusive")
