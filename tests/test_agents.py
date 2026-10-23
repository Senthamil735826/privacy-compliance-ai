import pytest
import time
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from backend.agents import (
    DynamicScheduler,
    EvaluationResult,
    GroqEvaluator,
    LLMEvaluator,
    TCAMConfig,
    TCAMResult,
    TCAMRouter,
)


# ============================================================================
# EVALUATION RESULT TESTS
# ============================================================================

def test_evaluation_result_valid():
    """Verify that EvaluationResult initializes correctly with valid fields."""
    result = EvaluationResult(
        agent_name="TestEvaluator",
        indicator_id="B19",
        decision="compliant",
        confidence=0.85,
        rationale="Policy explicitly outlines retention period.",
        evidence=["Data will be retained for 30 days."],
    )
    data = result.to_dict()
    assert data["agent_name"] == "TestEvaluator"
    assert data["indicator_id"] == "B19"
    assert data["decision"] == "compliant"
    assert data["confidence"] == 0.85
    assert len(data["evidence"]) == 1


def test_evaluation_result_invalid_decision():
    """Verify that an unknown decision string raises ValueError."""
    with pytest.raises(ValueError, match="Invalid decision"):
        EvaluationResult(
            agent_name="TestEvaluator",
            indicator_id="B19",
            decision="unknown_state",
            confidence=0.5,
            rationale="Ambiguous text.",
            evidence=[],
        )


def test_evaluation_result_confidence_bounds():
    """Verify that confidence out of bounds raises ValueError."""
    with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
        EvaluationResult(
            agent_name="TestEvaluator",
            indicator_id="B19",
            decision="compliant",
            confidence=1.2,
            rationale="Out of range",
            evidence=[],
        )

    with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
        EvaluationResult(
            agent_name="TestEvaluator",
            indicator_id="B19",
            decision="compliant",
            confidence=-0.1,
            rationale="Negative",
            evidence=[],
        )


def test_evaluation_result_empty_indicator_id():
    """Verify that empty indicator_id raises ValueError."""
    with pytest.raises(ValueError, match="indicator_id cannot be empty"):
        EvaluationResult(
            agent_name="TestEvaluator",
            indicator_id="   ",
            decision="inconclusive",
            confidence=0.5,
            rationale="Missing indicator ID",
            evidence=[],
        )


# ============================================================================
# TCAM ROUTER TESTS
# ============================================================================

def test_tcam_routing_thresholds():
    """Test low, medium, and high routing levels based on complexity."""
    router = TCAMRouter()

    # Low complexity: inherent difficulty = 0.1, full recall (1.0), low dispersion (0.0), low ambiguity (0.0)
    # Scarcity = 1.0 - (1/3*1 + 1/3*1 + 1/3*1) = 0.0
    # Complexity = 0.5 * 0.1 + 0.5 * 0 = 0.05 (< 0.4) -> 1 evaluator
    low = router.route(
        primary_indicator_id="A1",
        inherent_difficulty=0.1,
        evidence_recall=1.0,
        evidence_dispersion=0.0,
        semantic_ambiguity=0.0,
    )
    assert low.complexity_level == "low"
    assert low.evaluator_count == 1

    # High complexity: difficulty = 0.9, recall = 0.2, dispersion = 0.9, ambiguity = 0.9
    high = router.route(
        primary_indicator_id="A4",
        inherent_difficulty=0.9,
        evidence_recall=0.2,
        evidence_dispersion=0.9,
        semantic_ambiguity=0.9,
    )
    assert high.complexity_level == "high"
    assert high.evaluator_count == 5

    # Medium complexity: moderate values
    med = router.route(
        primary_indicator_id="A2",
        inherent_difficulty=0.5,
        evidence_recall=0.5,
        evidence_dispersion=0.5,
        semantic_ambiguity=0.5,
    )
    assert med.complexity_level == "medium"
    assert med.evaluator_count == 3


def test_tcam_input_validation():
    """Verify that TCAM validates input ranges and types."""
    router = TCAMRouter()

    with pytest.raises(ValueError, match="primary_indicator_id cannot be empty"):
        router.route(
            primary_indicator_id="",
            inherent_difficulty=0.5,
            evidence_recall=0.5,
            evidence_dispersion=0.5,
            semantic_ambiguity=0.5,
        )

    with pytest.raises(ValueError, match="inherent_difficulty must be between 0 and 1"):
        router.route(
            primary_indicator_id="A1",
            inherent_difficulty=1.5,
            evidence_recall=0.5,
            evidence_dispersion=0.5,
            semantic_ambiguity=0.5,
        )


# ============================================================================
# DYNAMIC SCHEDULER TESTS
# ============================================================================

def test_dynamic_scheduler_single():
    """Verify single evaluator execution."""
    scheduler = DynamicScheduler()
    router = TCAMRouter()

    tcam = router.route(
        primary_indicator_id="A1",
        inherent_difficulty=0.1,
        evidence_recall=1.0,
        evidence_dispersion=0.0,
        semantic_ambiguity=0.0,
    )
    assert tcam.evaluator_count == 1

    called = []
    def eval_1(*, evidence, indicator_id):
        called.append(1)
        return {"id": indicator_id, "evidence": evidence}

    results = scheduler.run(
        tcam,
        [eval_1],
        evidence="sample text",
        indicator_id="B1",
    )
    assert len(results) == 1
    assert called == [1]


def test_dynamic_scheduler_parallel_concurrency():
    """Verify parallel concurrent execution for multi-agent dispatch."""
    scheduler = DynamicScheduler()
    router = TCAMRouter()

    tcam = router.route(
        primary_indicator_id="A4",
        inherent_difficulty=0.9,
        evidence_recall=0.2,
        evidence_dispersion=0.9,
        semantic_ambiguity=0.9,
    )
    assert tcam.evaluator_count == 5

    def make_evaluator(idx, delay=0.1):
        def evaluate(*, evidence, indicator_id):
            time.sleep(delay)
            return {"idx": idx, "indicator_id": indicator_id}
        return evaluate

    evaluators = [make_evaluator(i) for i in range(5)]

    start = time.perf_counter()
    results = scheduler.run(
        tcam,
        evaluators,
        evidence="test evidence",
        indicator_id="B19",
    )
    elapsed = time.perf_counter() - start

    assert len(results) == 5
    assert [r["idx"] for r in results] == [0, 1, 2, 3, 4]
    # 5 evaluators sleeping 0.1s in parallel should finish well under 0.4s (sequential would be 0.5s+)
    assert elapsed < 0.35


def test_dynamic_scheduler_insufficient_evaluators():
    """Verify that insufficient evaluators raises ValueError."""
    scheduler = DynamicScheduler()
    router = TCAMRouter()

    tcam = router.route(
        primary_indicator_id="A4",
        inherent_difficulty=0.9,
        evidence_recall=0.2,
        evidence_dispersion=0.9,
        semantic_ambiguity=0.9,
    )
    assert tcam.evaluator_count == 5

    def dummy(*, evidence, indicator_id):
        return {}

    with pytest.raises(ValueError, match="TCAM selected 5 evaluators, but only 2 were provided"):
        scheduler.run(tcam, [dummy, dummy], evidence="", indicator_id="B1")


# ============================================================================
# MOCK EVALUATOR TESTS
# ============================================================================

from backend.agents.mock_evaluator import MockPrivacyEvaluator


def test_mock_evaluator_protocol_compliance():
    """Verify that MockPrivacyEvaluator adheres to LLMEvaluator protocol."""
    evaluator = MockPrivacyEvaluator("Agent-Alpha")
    assert isinstance(evaluator, LLMEvaluator)
    assert evaluator.agent_name == "Agent-Alpha"


def test_mock_evaluator_with_evidence():
    """Verify evaluation when policy evidence is supplied."""
    evaluator = MockPrivacyEvaluator("Agent-Alpha", confidence=0.9)
    result = evaluator.evaluate(
        evidence="We collect user email addresses for account recovery.",
        indicator_id="B1",
        indicator_description="Basic policy identification",
    )

    assert result.agent_name == "Agent-Alpha"
    assert result.indicator_id == "B1"
    assert result.decision == "inconclusive"
    assert result.confidence == 0.9
    assert len(result.evidence) == 1
    assert "We collect user email" in result.evidence[0]


def test_mock_evaluator_without_evidence():
    """Verify evaluation when empty evidence is supplied."""
    evaluator = MockPrivacyEvaluator("Agent-Beta")
    result = evaluator.evaluate(
        evidence="   ",
        indicator_id="B2",
        indicator_description="Scope of collection",
    )

    assert result.agent_name == "Agent-Beta"
    assert result.decision == "inconclusive"
    assert result.rationale == "No policy evidence was provided."
    assert result.evidence == []


def test_mock_evaluator_integration_with_scheduler():
    """Verify that MockPrivacyEvaluator instances can be passed directly to DynamicScheduler."""
    scheduler = DynamicScheduler()
    router = TCAMRouter()

    tcam = router.route(
        primary_indicator_id="A2",
        inherent_difficulty=0.5,
        evidence_recall=0.5,
        evidence_dispersion=0.5,
        semantic_ambiguity=0.5,
    )
    assert tcam.evaluator_count == 3

    evaluators = [
        MockPrivacyEvaluator(f"Mock-Agent-{i}")
        for i in range(3)
    ]

    results = scheduler.run(
        tcam,
        evaluators,
        evidence="Data is stored securely on encrypted cloud servers.",
        indicator_id="B7",
    )

    assert len(results) == 3
    assert [r.agent_name for r in results] == ["Mock-Agent-0", "Mock-Agent-1", "Mock-Agent-2"]
    assert all(r.decision == "inconclusive" for r in results)


# ============================================================================
# PRIVACY AGENT PIPELINE TESTS
# ============================================================================

from backend.agents.agent_pipeline import PrivacyAgentPipeline


def test_pipeline_empty_evaluators_raises():
    """Verify that creating a pipeline with no evaluators raises ValueError."""
    with pytest.raises(ValueError, match="At least one evaluator is required"):
        PrivacyAgentPipeline(
            router=TCAMRouter(),
            scheduler=DynamicScheduler(),
            evaluators=[],
        )


def test_pipeline_low_complexity_flow():
    """Verify end-to-end evaluation with low complexity triggering 1 evaluator."""
    pipeline = PrivacyAgentPipeline(
        router=TCAMRouter(),
        scheduler=DynamicScheduler(),
        evaluators=[
            MockPrivacyEvaluator("Agent-1"),
            MockPrivacyEvaluator("Agent-2"),
            MockPrivacyEvaluator("Agent-3"),
        ],
    )

    result = pipeline.evaluate_indicator(
        primary_indicator_id="A1",
        indicator_id="B1",
        indicator_description="Policy title & effective date",
        evidence="Effective Date: 2026-01-01",
        inherent_difficulty=0.1,
        evidence_recall=1.0,
        evidence_dispersion=0.0,
        semantic_ambiguity=0.0,
    )

    assert result["primary_indicator_id"] == "A1"
    assert result["indicator_id"] == "B1"
    assert result["tcam"]["complexity_level"] == "low"
    assert result["tcam"]["evaluator_count"] == 1
    assert result["evaluator_count"] == 1
    assert len(result["evaluations"]) == 1
    assert result["evaluations"][0]["agent_name"] == "Agent-1"


def test_pipeline_high_complexity_flow():
    """Verify end-to-end evaluation with high complexity triggering 5 evaluators."""
    pipeline = PrivacyAgentPipeline(
        router=TCAMRouter(),
        scheduler=DynamicScheduler(),
        evaluators=[
            MockPrivacyEvaluator(f"Agent-{i}")
            for i in range(1, 6)
        ],
    )

    result = pipeline.evaluate_indicator(
        primary_indicator_id="A4",
        indicator_id="B19",
        indicator_description="Purpose of collection",
        evidence="We collect personal data to fulfill customer services.",
        inherent_difficulty=0.9,
        evidence_recall=0.2,
        evidence_dispersion=0.9,
        semantic_ambiguity=0.9,
    )

    assert result["tcam"]["complexity_level"] == "high"
    assert result["tcam"]["evaluator_count"] == 5
    assert result["evaluator_count"] == 5
    assert len(result["evaluations"]) == 5
    assert all(item["decision"] == "inconclusive" for item in result["evaluations"])


# ============================================================================
# GROQ EVALUATOR TESTS
# ============================================================================

def test_groq_evaluator_protocol():
    """Verify GroqEvaluator adheres to LLMEvaluator protocol."""
    import os
    os.environ["GROQ_API_KEY"] = "mock_test_key"
    evaluator = GroqEvaluator(api_key="mock_test_key")
    assert isinstance(evaluator, LLMEvaluator)
    assert evaluator.agent_name == "groq"


def test_groq_evaluator_empty_evidence():
    """Verify GroqEvaluator returns inconclusive on empty evidence without calling API."""
    evaluator = GroqEvaluator(api_key="mock_test_key")
    result = evaluator.evaluate(
        evidence="   ",
        indicator_id="B19",
        indicator_description="Test indicator",
    )
    assert result.decision == "inconclusive"
    assert result.confidence == 0.0
    assert result.agent_name == "groq"


def test_groq_evaluator_parse_valid_json():
    """Verify GroqEvaluator correctly parses structured JSON."""
    raw = '{"decision": "compliant", "confidence": 0.9, "rationale": "Valid rationale", "evidence": ["quote"]}'
    parsed = GroqEvaluator._parse_response(raw, "B19")
    assert parsed["decision"] == "compliant"
    assert parsed["confidence"] == 0.9
    assert parsed["rationale"] == "Valid rationale"
    assert parsed["evidence"] == ["quote"]


def test_groq_evaluator_parse_markdown_json():
    """Verify GroqEvaluator correctly extracts JSON within markdown blocks."""
    raw = "```json\n{\"decision\": \"non_compliant\", \"confidence\": 0.8, \"rationale\": \"Missing term\", \"evidence\": []}\n```"
    parsed = GroqEvaluator._parse_response(raw, "B19")
    assert parsed["decision"] == "non_compliant"
    assert parsed["confidence"] == 0.8
    assert parsed["evidence"] == []


def test_groq_evaluator_parse_invalid_decision():
    """Verify GroqEvaluator raises error on unrecognized decision."""
    raw = '{"decision": "maybe", "confidence": 0.5, "rationale": "Uncertain", "evidence": []}'
    with pytest.raises(ValueError, match="Invalid decision"):
        GroqEvaluator._parse_response(raw, "B19")




