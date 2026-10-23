"""Dynamic scheduler for TCAM-selected privacy compliance evaluators."""

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Sequence

from backend.agents.tcam_router import TCAMResult


class DynamicScheduler:
    """Dispatch the number of evaluators selected by TCAM."""

    ALLOWED_COUNTS = {1, 3, 5}

    def run(
        self,
        tcam_result: TCAMResult,
        evaluators: Sequence[Callable[..., Any]],
        *,
        evidence: str,
        indicator_id: str,
        allow_partial: bool = False,
    ) -> list[Any]:
        """
        Execute the selected evaluators concurrently.

        Each evaluator must accept:
            evidence=<policy evidence>
            indicator_id=<secondary indicator ID>

        This scheduler does not implement LLM providers or aggregation.
        Those are separate components.
        """
        count = tcam_result.evaluator_count

        if count not in self.ALLOWED_COUNTS:
            raise ValueError(
                f"Unsupported evaluator count: {count}. Expected 1, 3, or 5."
            )

        if len(evaluators) < count:
            if not allow_partial:
                raise ValueError(
                    f"TCAM selected {count} evaluators, but only "
                    f"{len(evaluators)} were provided."
                )
            count = len(evaluators)

        if count == 0:
            return []

        selected = evaluators[:count]

        if count == 1:
            return [
                selected[0](
                    evidence=evidence,
                    indicator_id=indicator_id,
                )
            ]

        with ThreadPoolExecutor(max_workers=count) as executor:
            futures = [
                executor.submit(
                    evaluator,
                    evidence=evidence,
                    indicator_id=indicator_id,
                )
                for evaluator in selected
            ]

            # Preserve evaluator order in the returned results.
            return [future.result() for future in futures]