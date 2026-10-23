"""Mock evaluator for testing the agent pipeline without API calls."""

from backend.agents.llm_evaluator import EvaluationResult


class MockPrivacyEvaluator:
    """Simulates an evaluator until a real LLM is connected."""

    def __init__(self, name: str, confidence: float = 0.85):
        self._agent_name = name
        self._confidence = confidence

    @property
    def agent_name(self) -> str:
        return self._agent_name

    def __call__(
        self,
        *,
        evidence: str,
        indicator_id: str,
        indicator_description: str = "",
    ) -> EvaluationResult:
        return self.evaluate(
            evidence=evidence,
            indicator_id=indicator_id,
            indicator_description=indicator_description,
        )

    def evaluate(
        self,
        *,
        evidence: str,
        indicator_id: str,
        indicator_description: str = "",
    ) -> EvaluationResult:
        if not evidence.strip():
            decision = "inconclusive"
            rationale = "No policy evidence was provided."
            matched_evidence = []
        else:
            decision = "inconclusive"
            rationale = (
                "Mock evaluation only. A real LLM must assess "
                "the evidence against the indicator requirements."
            )
            matched_evidence = [evidence[:300]]

        return EvaluationResult(
            agent_name=self.agent_name,
            indicator_id=indicator_id,
            decision=decision,
            confidence=self._confidence,
            rationale=rationale,
            evidence=matched_evidence,
        )