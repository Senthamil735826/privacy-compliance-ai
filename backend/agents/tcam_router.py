"""
Task Complexity Assessment Model (TCAM).

Implements evidence-quality-driven routing for privacy compliance
evaluation, following the TCAM equations and thresholds in the
research paper.

Routing thresholds:
    theta < 0.4       -> 1 evaluator
    0.4 <= theta < 0.7 -> 3 evaluators
    theta >= 0.7      -> 5 evaluators
"""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class TCAMConfig:
    """Weights used to calculate task complexity and evidence scarcity."""

    inherent_difficulty_weight: float = 0.5
    evidence_scarcity_weight: float = 0.5

    evidence_recall_weight: float = 1.0 / 3.0
    evidence_dispersion_weight: float = 1.0 / 3.0
    semantic_ambiguity_weight: float = 1.0 / 3.0

    single_agent_threshold: float = 0.4
    three_agent_threshold: float = 0.7


@dataclass(frozen=True)
class TCAMResult:
    """Structured result produced by the TCAM router."""

    primary_indicator_id: str
    inherent_difficulty: float
    evidence_recall: float
    evidence_dispersion: float
    semantic_ambiguity: float
    evidence_scarcity: float
    complexity_score: float
    complexity_level: str
    evaluator_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TCAMRouter:
    """
    Deterministic router that selects the evaluation budget.

    All evidence metrics must be normalized to [0, 1]:
      - evidence_recall: 1 means all expected evidence was retrieved.
      - evidence_dispersion: 1 means evidence is highly dispersed.
      - semantic_ambiguity: 1 means evidence is highly ambiguous.
    """

    def __init__(self, config: TCAMConfig | None = None) -> None:
        self.config = config or TCAMConfig()
        self._validate_config()

    @staticmethod
    def _validate_unit_interval(name: str, value: float) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{name} must be a number.")

        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be between 0 and 1.")

    def _validate_config(self) -> None:
        cfg = self.config

        weight_pairs = (
            (
                cfg.inherent_difficulty_weight,
                cfg.evidence_scarcity_weight,
                "complexity weights",
            ),
            (
                cfg.evidence_recall_weight,
                cfg.evidence_dispersion_weight,
                cfg.semantic_ambiguity_weight,
                "evidence weights",
            ),
        )

        for *weights, label in weight_pairs:
            if any(weight < 0 for weight in weights):
                raise ValueError(f"{label} cannot be negative.")

            if abs(sum(weights) - 1.0) > 1e-9:
                raise ValueError(f"{label} must sum to 1.")

        if not (
            0.0 < cfg.single_agent_threshold
            < cfg.three_agent_threshold
            < 1.0
        ):
            raise ValueError("Routing thresholds must be ordered within (0, 1).")

    def route(
        self,
        *,
        primary_indicator_id: str,
        inherent_difficulty: float,
        evidence_recall: float,
        evidence_dispersion: float,
        semantic_ambiguity: float,
    ) -> TCAMResult:
        """Calculate complexity and choose 1, 3, or 5 evaluators."""

        if not isinstance(primary_indicator_id, str):
            raise TypeError("primary_indicator_id must be a string.")

        if not primary_indicator_id.strip():
            raise ValueError("primary_indicator_id cannot be empty.")

        metrics = {
            "inherent_difficulty": inherent_difficulty,
            "evidence_recall": evidence_recall,
            "evidence_dispersion": evidence_dispersion,
            "semantic_ambiguity": semantic_ambiguity,
        }

        for name, value in metrics.items():
            self._validate_unit_interval(name, value)

        cfg = self.config

        # S_i = 1 - [beta1*R + beta2*(1-D) + beta3*(1-A)]
        evidence_scarcity = 1.0 - (
            cfg.evidence_recall_weight * evidence_recall
            + cfg.evidence_dispersion_weight * (1.0 - evidence_dispersion)
            + cfg.semantic_ambiguity_weight * (1.0 - semantic_ambiguity)
        )

        # theta_i = w_h*H_i + w_s*S_i
        complexity_score = (
            cfg.inherent_difficulty_weight * inherent_difficulty
            + cfg.evidence_scarcity_weight * evidence_scarcity
        )

        # Protect against insignificant floating-point rounding.
        evidence_scarcity = min(1.0, max(0.0, evidence_scarcity))
        complexity_score = min(1.0, max(0.0, complexity_score))

        if complexity_score < cfg.single_agent_threshold:
            evaluator_count = 1
            complexity_level = "low"
        elif complexity_score < cfg.three_agent_threshold:
            evaluator_count = 3
            complexity_level = "medium"
        else:
            evaluator_count = 5
            complexity_level = "high"

        return TCAMResult(
            primary_indicator_id=primary_indicator_id.strip(),
            inherent_difficulty=float(inherent_difficulty),
            evidence_recall=float(evidence_recall),
            evidence_dispersion=float(evidence_dispersion),
            semantic_ambiguity=float(semantic_ambiguity),
            evidence_scarcity=evidence_scarcity,
            complexity_score=complexity_score,
            complexity_level=complexity_level,
            evaluator_count=evaluator_count,
        )

