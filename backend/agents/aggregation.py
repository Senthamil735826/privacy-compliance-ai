"""Transparent multi-agent consensus aggregation for privacy compliance decisions.

DISCLAIMER:
This module implements a weighted consensus voting aggregator with transparent
failure reporting. It is NOT Iterative Robust Aggregation (IRA). Formal IRA
requires iterative multi-round refinement and cross-agent critique protocols,
which can be implemented as a dedicated enhancement.
"""

from dataclasses import asdict, dataclass
from typing import Any, List, Optional

from backend.agents.llm_evaluator import EvaluationResult


@dataclass(frozen=True)
class AggregationResult:
    """Structured result of multi-agent evaluation aggregation."""

    final_decision: str
    final_confidence: float
    consensus_reached: bool
    has_disagreement: bool
    vote_counts: dict[str, int]
    total_requested: int
    total_selected: int
    total_succeeded: int
    total_failed: int
    evaluations: list[dict[str, Any]]
    failed_evaluations: list[dict[str, Any]]
    summary_rationale: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ConsensusAggregator:
    """Aggregate multiple LLM evaluation results into an audited decision."""

    MIN_CONSENSUS_MULTI_AGENT = 2

    @classmethod
    def aggregate(
        cls,
        *,
        indicator_id: str,
        tcam_evaluator_count: int,
        successful_evaluations: List[EvaluationResult],
        failed_evaluations: Optional[List[dict[str, Any]]] = None,
    ) -> AggregationResult:
        """
        Aggregate opinions from successful evaluators.
        
        Failures are strictly excluded from the voting denominator and reported
        separately with their operational errors.
        """
        failed_list = failed_evaluations or []
        success_count = len(successful_evaluations)
        total_selected = success_count + len(failed_list)

        # Count votes
        votes = {
            "compliant": 0,
            "non_compliant": 0,
            "inconclusive": 0,
        }

        for eval_res in successful_evaluations:
            if eval_res.decision in votes:
                votes[eval_res.decision] += 1
            else:
                votes["inconclusive"] += 1

        evaluations_dict = [e.to_dict() for e in successful_evaluations]

        # Case 1: Zero successful evaluators
        if success_count == 0:
            return AggregationResult(
                final_decision="inconclusive",
                final_confidence=0.0,
                consensus_reached=False,
                has_disagreement=False,
                vote_counts=votes,
                total_requested=tcam_evaluator_count,
                total_selected=total_selected,
                total_succeeded=0,
                total_failed=len(failed_list),
                evaluations=[],
                failed_evaluations=failed_list,
                summary_rationale=(
                    f"All {len(failed_list)} selected evaluators failed due to operational errors. "
                    "No valid compliance opinions were obtained."
                ),
            )

        # Case 2: Exactly 1 successful evaluator
        if success_count == 1:
            single = successful_evaluations[0]
            # If TCAM requested 3 or 5 but only 1 succeeded, consensus is incomplete
            consensus = (tcam_evaluator_count == 1)
            return AggregationResult(
                final_decision=single.decision,
                final_confidence=single.confidence,
                consensus_reached=consensus,
                has_disagreement=False,
                vote_counts=votes,
                total_requested=tcam_evaluator_count,
                total_selected=total_selected,
                total_succeeded=1,
                total_failed=len(failed_list),
                evaluations=evaluations_dict,
                failed_evaluations=failed_list,
                summary_rationale=(
                    f"Decision based on single successful evaluator ({single.agent_name}): {single.rationale}"
                    + (f" ({len(failed_list)} evaluators failed)." if failed_list else "")
                ),
            )

        # Case 3: Multiple successful evaluators
        # Determine non-inconclusive opinions
        substantive_decisions = [v for k, v in votes.items() if k != "inconclusive" and v > 0]
        has_substantive_conflict = votes["compliant"] > 0 and votes["non_compliant"] > 0
        has_disagreement = len([v for v in votes.values() if v > 0]) > 1

        # Check for strict majority or plurality
        max_votes = max(votes.values())
        top_decisions = [k for k, v in votes.items() if v == max_votes]

        # Contradiction: tie between compliant and non_compliant
        if "compliant" in top_decisions and "non_compliant" in top_decisions:
            final_decision = "inconclusive"
            avg_conf = sum(e.confidence for e in successful_evaluations) / success_count
            return AggregationResult(
                final_decision="inconclusive",
                final_confidence=round(avg_conf * 0.5, 2),  # penalize for conflict
                consensus_reached=False,
                has_disagreement=True,
                vote_counts=votes,
                total_requested=tcam_evaluator_count,
                total_selected=total_selected,
                total_succeeded=success_count,
                total_failed=len(failed_list),
                evaluations=evaluations_dict,
                failed_evaluations=failed_list,
                summary_rationale=(
                    f"Material contradiction between evaluators (compliant: {votes['compliant']}, "
                    f"non_compliant: {votes['non_compliant']}). Marked inconclusive."
                ),
            )

        winning_decision = top_decisions[0]

        # Calculate confidence from evaluators supporting winning decision
        winning_evals = [e for e in successful_evaluations if e.decision == winning_decision]
        avg_winning_confidence = sum(e.confidence for e in winning_evals) / len(winning_evals)

        # Consensus confidence incorporates agreement ratio
        agreement_ratio = max_votes / success_count
        combined_confidence = round(avg_winning_confidence * (0.5 + 0.5 * agreement_ratio), 2)

        consensus_reached = (
            max_votes >= cls.MIN_CONSENSUS_MULTI_AGENT
            and not has_substantive_conflict
        )

        winning_rationales = "; ".join(f"[{e.agent_name}]: {e.rationale}" for e in winning_evals)

        return AggregationResult(
            final_decision=winning_decision,
            final_confidence=combined_confidence,
            consensus_reached=consensus_reached,
            has_disagreement=has_disagreement,
            vote_counts=votes,
            total_requested=tcam_evaluator_count,
            total_selected=total_selected,
            total_succeeded=success_count,
            total_failed=len(failed_list),
            evaluations=evaluations_dict,
            failed_evaluations=failed_list,
            summary_rationale=f"Majority consensus ({max_votes}/{success_count}): {winning_rationales}",
        )
