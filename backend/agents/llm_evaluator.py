"""Provider-independent interface for privacy compliance evaluators."""

from dataclasses import asdict, dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class EvaluationResult:
    """Structured result returned by a privacy compliance evaluator."""

    agent_name: str
    indicator_id: str
    decision: str
    confidence: float
    rationale: str
    evidence: list[str]

    def __post_init__(self) -> None:
        allowed_decisions = {
            "compliant",
            "non_compliant",
            "inconclusive",
        }

        if self.decision not in allowed_decisions:
            raise ValueError(
                f"Invalid decision: {self.decision}"
            )

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "Confidence must be between 0 and 1."
            )

        if not self.indicator_id.strip():
            raise ValueError("indicator_id cannot be empty.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@runtime_checkable
class LLMEvaluator(Protocol):
    """Contract that every LLM evaluator implementation must follow."""

    @property
    def agent_name(self) -> str:
        ...

    def evaluate(
        self,
        *,
        evidence: str,
        indicator_id: str,
        indicator_description: str,
    ) -> EvaluationResult:
        ...

