from __future__ import annotations

from dataclasses import replace
from typing import Any

from ..domain.model import ObjectiveKind, Problem
from ..search.dispatch import run_search
from ..search.run import RunConfig
from .run_metrics import build_run_metrics


def compare_objectives(problem: Problem, config: RunConfig) -> list[dict[str, Any]]:
    """Run the same algorithm and seed once per objective for report comparisons."""
    comparisons = []
    for objective in (ObjectiveKind.TOTAL_VALUE, ObjectiveKind.VALUE_PER_URGENCY):
        objective_config = replace(config, objective=objective)
        result = run_search(problem, objective_config)
        comparisons.append(build_run_metrics(problem, result))
    return comparisons


__all__ = ["compare_objectives"]
