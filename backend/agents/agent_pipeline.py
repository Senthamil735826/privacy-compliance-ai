"""Integrate TCAM routing, evaluator scheduling, and transparent aggregation."""

from typing import Any, List

from backend.agents.aggregation import ConsensusAggregator
from backend.agents.dynamic_scheduler import DynamicScheduler
from backend.agents.llm_evaluator import EvaluationResult, LLMEvaluator
from backend.agents.tcam_router import TCAMRouter


class PrivacyAgentPipeline:
    """Coordinate complexity assessment, evaluator execution, and consensus aggregation."""

    def __init__(
        self,
        router: TCAMRouter,
        scheduler: DynamicScheduler,
        evaluators: list[LLMEvaluator],
    ) -> None:
        if not evaluators:
            raise ValueError("At least one evaluator is required.")

        # Ensure unique evaluators by agent_name
        seen = set()
        unique_evaluators = []
        for e in evaluators:
            name = getattr(e, "agent_name", str(e))
            if name not in seen:
                seen.add(name)
                unique_evaluators.append(e)

        self.router = router
        self.scheduler = scheduler
        self.evaluators = unique_evaluators

    def evaluate_indicator(
        self,
        *,
        primary_indicator_id: str,
        indicator_id: str,
        indicator_description: str,
        evidence: str,
        inherent_difficulty: float,
        evidence_recall: float,
        evidence_dispersion: float,
        semantic_ambiguity: float,
    ) -> dict[str, Any]:
        """Route, execute evaluators with fault isolation, and aggregate results."""

        tcam_result = self.router.route(
            primary_indicator_id=primary_indicator_id,
            inherent_difficulty=inherent_difficulty,
            evidence_recall=evidence_recall,
            evidence_dispersion=evidence_dispersion,
            semantic_ambiguity=semantic_ambiguity,
        )

        def make_task(evaluator: LLMEvaluator):
            def task(*, evidence: str, indicator_id: str):
                try:
                    result = evaluator.evaluate(
                        evidence=evidence,
                        indicator_id=indicator_id,
                        indicator_description=indicator_description,
                    )
                    return {"success": True, "result": result, "agent_name": evaluator.agent_name}
                except Exception as exc:
                    return {
                        "success": False,
                        "agent_name": getattr(evaluator, "agent_name", "unknown"),
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                    }

            return task

        tasks = [make_task(evaluator) for evaluator in self.evaluators]

        raw_outcomes = self.scheduler.run(
            tcam_result,
            tasks,
            evidence=evidence,
            indicator_id=indicator_id,
            allow_partial=True,
        )

        successful_results: List[EvaluationResult] = []
        failed_results: List[dict[str, Any]] = []

        for outcome in raw_outcomes:
            if isinstance(outcome, dict) and outcome.get("success") is False:
                failed_results.append({
                    "agent_name": outcome.get("agent_name", "unknown"),
                    "indicator_id": indicator_id,
                    "error_type": outcome.get("error_type", "UnknownError"),
                    "message": outcome.get("error_message", "Unknown failure"),
                })
            elif isinstance(outcome, dict) and outcome.get("success") is True:
                successful_results.append(outcome["result"])
            elif isinstance(outcome, EvaluationResult):
                successful_results.append(outcome)

        # Run transparent consensus aggregation over successful opinions
        aggregation = ConsensusAggregator.aggregate(
            indicator_id=indicator_id,
            tcam_evaluator_count=tcam_result.evaluator_count,
            successful_evaluations=successful_results,
            failed_evaluations=failed_results,
        )

        selected_agents = [
            getattr(e, "agent_name", "unknown")
            for e in self.evaluators[:tcam_result.evaluator_count]
        ]

        return {
            "primary_indicator_id": primary_indicator_id,
            "indicator_id": indicator_id,
            "tcam": tcam_result.to_dict(),
            "evaluator_count": len(successful_results),
            "requested_evaluators": tcam_result.evaluator_count,
            "selected_evaluators": selected_agents,
            "evaluations": [result.to_dict() for result in successful_results],
            "failed_evaluations": failed_results,
            "aggregation": aggregation.to_dict(),
        }
