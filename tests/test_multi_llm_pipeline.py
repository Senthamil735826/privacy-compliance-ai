"""Integration tests for Multi-LLM TCAM Routing, Dynamic Scheduler, and Aggregation."""

import pytest
from unittest.mock import MagicMock

from backend.agents.agent_pipeline import PrivacyAgentPipeline
from backend.agents.aggregation import ConsensusAggregator
from backend.agents.claude_evaluator import ClaudeEvaluator
from backend.agents.dynamic_scheduler import DynamicScheduler
from backend.agents.llm_evaluator import EvaluationResult
from backend.agents.mock_evaluator import MockPrivacyEvaluator
from backend.agents.provider_errors import QuotaExhaustedError
from backend.agents.tcam_router import TCAMRouter


class FixedResultEvaluator:
    """Helper evaluator that returns a pre-configured EvaluationResult or raises an error."""

    def __init__(self, name: str, result: EvaluationResult = None, error: Exception = None):
        self._name = name
        self._result = result
        self._error = error

    @property
    def agent_name(self) -> str:
        return self._name

    def evaluate(self, *, evidence: str, indicator_id: str, indicator_description: str) -> EvaluationResult:
        if self._error:
            raise self._error
        return self._result or EvaluationResult(
            agent_name=self._name,
            indicator_id=indicator_id,
            decision="compliant",
            confidence=0.9,
            rationale=f"{self._name} compliant rationale",
            evidence=["valid quote"],
        )


# ============================================================================
# AGGREGATION UNIT TESTS
# ============================================================================

def test_aggregation_unanimous_compliant():
    """Verify unanimous compliant decisions produce a compliant consensus."""
    evals = [
        EvaluationResult("claude", "B1", "compliant", 0.95, "Explicit mention", ["quote"]),
        EvaluationResult("gemini", "B1", "compliant", 0.90, "Explicit mention", ["quote"]),
        EvaluationResult("groq", "B1", "compliant", 0.85, "Explicit mention", ["quote"]),
    ]
    agg = ConsensusAggregator.aggregate(
        indicator_id="B1",
        tcam_evaluator_count=3,
        successful_evaluations=evals,
    )
    assert agg.final_decision == "compliant"
    assert agg.consensus_reached is True
    assert agg.has_disagreement is False
    assert agg.vote_counts["compliant"] == 3
    assert agg.total_succeeded == 3
    assert agg.total_failed == 0


def test_aggregation_conflicting_votes_returns_inconclusive():
    """Verify tie or material contradiction between compliant and non_compliant yields inconclusive."""
    evals = [
        EvaluationResult("claude", "B1", "compliant", 0.9, "Has term", ["quote"]),
        EvaluationResult("gemini", "B1", "non_compliant", 0.9, "Lacks term", ["quote"]),
    ]
    agg = ConsensusAggregator.aggregate(
        indicator_id="B1",
        tcam_evaluator_count=2,
        successful_evaluations=evals,
    )
    assert agg.final_decision == "inconclusive"
    assert agg.consensus_reached is False
    assert agg.has_disagreement is True
    assert "Material contradiction" in agg.summary_rationale


def test_aggregation_excludes_provider_failures_from_denominator():
    """Verify provider failures do not lower the vote ratio or become inconclusive votes."""
    evals = [
        EvaluationResult("claude", "B1", "compliant", 0.9, "Supported", ["quote"]),
        EvaluationResult("groq", "B1", "compliant", 0.85, "Supported", ["quote"]),
    ]
    failed = [
        {
            "agent_name": "openai",
            "indicator_id": "B1",
            "error_type": "QuotaExhaustedError",
            "message": "insufficient_quota",
        }
    ]
    agg = ConsensusAggregator.aggregate(
        indicator_id="B1",
        tcam_evaluator_count=3,
        successful_evaluations=evals,
        failed_evaluations=failed,
    )
    # The 1 failure is reported in failed_evaluations, NOT in vote_counts
    assert agg.vote_counts["inconclusive"] == 0
    assert agg.vote_counts["compliant"] == 2
    assert agg.total_succeeded == 2
    assert agg.total_failed == 1
    assert agg.final_decision == "compliant"


# ============================================================================
# PIPELINE & SCHEDULER PARTIAL AVAILABILITY TESTS
# ============================================================================

def test_pipeline_with_claude_and_mock():
    """Verify ClaudeEvaluator integrates smoothly into PrivacyAgentPipeline."""
    claude = ClaudeEvaluator(api_key="mock_key")
    claude._client = MagicMock()
    claude._client.messages.create.return_value.content = [
        MagicMock(text='{"decision": "compliant", "confidence": 0.92, "rationale": "Clear policy name.", "evidence": ["Policy Title"]}')
    ]

    pipeline = PrivacyAgentPipeline(
        router=TCAMRouter(),
        scheduler=DynamicScheduler(),
        evaluators=[claude],
    )

    result = pipeline.evaluate_indicator(
        primary_indicator_id="A1",
        indicator_id="B1",
        indicator_description="Policy Name",
        evidence="Policy Title: Official Smart Device Privacy Policy.",
        inherent_difficulty=0.2,
        evidence_recall=0.9,
        evidence_dispersion=0.1,
        semantic_ambiguity=0.1,
    )

    assert result["primary_indicator_id"] == "A1"
    assert result["indicator_id"] == "B1"
    assert result["evaluator_count"] == 1
    assert len(result["evaluations"]) == 1
    assert result["evaluations"][0]["agent_name"] == "claude"
    assert result["evaluations"][0]["decision"] == "compliant"
    assert result["aggregation"]["final_decision"] == "compliant"


def test_pipeline_partial_provider_availability():
    """Verify pipeline runs available providers when TCAM requests 5 but only 2 are available."""
    # High complexity triggers TCAM count = 5
    evaluator1 = FixedResultEvaluator("agent_1")
    evaluator2 = FixedResultEvaluator("agent_2")

    pipeline = PrivacyAgentPipeline(
        router=TCAMRouter(),
        scheduler=DynamicScheduler(),
        evaluators=[evaluator1, evaluator2],  # Only 2 distinct evaluators configured
    )

    result = pipeline.evaluate_indicator(
        primary_indicator_id="A4",
        indicator_id="B19",
        indicator_description="Retention Period",
        evidence="We retain data for 12 months.",
        inherent_difficulty=0.9,
        evidence_recall=0.2,
        evidence_dispersion=0.9,
        semantic_ambiguity=0.9,
    )

    # TCAM requested 5
    assert result["tcam"]["evaluator_count"] == 5
    assert result["requested_evaluators"] == 5
    # Actual successful count is 2 (never falsely claimed as 5)
    assert result["evaluator_count"] == 2
    assert len(result["evaluations"]) == 2
    assert result["aggregation"]["total_requested"] == 5
    assert result["aggregation"]["total_succeeded"] == 2


def test_pipeline_fault_isolation_when_provider_fails():
    """Verify that a provider raising QuotaExhaustedError does not abort other providers."""
    good_evaluator = FixedResultEvaluator("claude")
    broken_evaluator = FixedResultEvaluator(
        "openai",
        error=QuotaExhaustedError("openai", "B1", "Credit balance exhausted")
    )

    pipeline = PrivacyAgentPipeline(
        router=TCAMRouter(),
        scheduler=DynamicScheduler(),
        evaluators=[good_evaluator, broken_evaluator],
    )

    result = pipeline.evaluate_indicator(
        primary_indicator_id="A1",
        indicator_id="B1",
        indicator_description="Policy Name",
        evidence="Policy Title: Smart App Policy.",
        inherent_difficulty=0.5,
        evidence_recall=0.5,
        evidence_dispersion=0.5,
        semantic_ambiguity=0.5,
    )

    # 1 succeeded, 1 failed
    assert result["evaluator_count"] == 1
    assert len(result["evaluations"]) == 1
    assert result["evaluations"][0]["agent_name"] == "claude"
    assert len(result["failed_evaluations"]) == 1
    assert result["failed_evaluations"][0]["agent_name"] == "openai"
    assert result["failed_evaluations"][0]["error_type"] == "QuotaExhaustedError"
    # Aggregation reflects the successful evaluator's opinion
    assert result["aggregation"]["final_decision"] == "compliant"
    assert result["aggregation"]["total_failed"] == 1
