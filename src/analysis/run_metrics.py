from __future__ import annotations

from collections import defaultdict
from statistics import fmean
from typing import Any

from domain.model import Problem
from domain.objectives import summarize_state
from search.run import AlgorithmKind, SearchResult, TracePoint


ALGORITHM_NAMES = {
    AlgorithmKind.STEEPEST_ASCENT: "Hill Climbing · Steepest Ascent",
    AlgorithmKind.SIDEWAYS: "Hill Climbing · Sideways",
    AlgorithmKind.STOCHASTIC: "Hill Climbing · Stochastic",
    AlgorithmKind.RANDOM_RESTART: "Hill Climbing · Random Restart",
    AlgorithmKind.SIMULATED_ANNEALING: "Simulated Annealing",
    AlgorithmKind.GENETIC_ALGORITHM: "Genetic Algorithm",
}


def iteration_count(result: SearchResult) -> int:
    """Menghitung langkah utama yang tercatat pada trajectory."""
    if result.algorithm is AlgorithmKind.GENETIC_ALGORITHM:
        return max(
            (point.generation or 0 for point in result.trace),
            default=0,
        )
    if result.algorithm is AlgorithmKind.RANDOM_RESTART:
        return sum(
            point.iteration_in_restart is not None
            and point.iteration_in_restart > 0
            for point in result.trace
        )
    return max(0, len(result.trace) - 1)


def _restart_metrics(result: SearchResult) -> dict[str, Any]:
    groups: dict[int, list[TracePoint]] = defaultdict(list)
    for point in result.trace:
        if point.restart is not None:
            groups[point.restart].append(point)

    ordered = sorted(groups)
    details = []
    for index, restart in enumerate(ordered):
        points = groups[restart]
        start_evaluations = points[0].evaluations
        if index + 1 < len(ordered):
            next_start = groups[ordered[index + 1]][0].evaluations
            evaluations = next_start - start_evaluations
        else:
            evaluations = result.evaluations_used - start_evaluations + 1
        details.append(
            {
                "restart": restart,
                "iterations": max(
                    (point.iteration_in_restart or 0 for point in points),
                    default=0,
                ),
                "evaluations": max(1, evaluations),
                "initial_objective": points[0].objective,
                "final_objective": points[-1].objective,
            }
        )

    best_restart = next(
        (
            point.restart
            for point in result.trace
            if point.restart is not None
            and point.objective == result.best_objective
        ),
        None,
    )
    return {
        "attempts": len(ordered),
        "restarts_completed": max(0, len(ordered) - 1),
        "best_restart": best_restart,
        "per_restart": details,
    }


def algorithm_metrics(result: SearchResult) -> dict[str, Any]:
    """Menyusun metrics khusus berdasarkan jenis algoritma."""
    points = result.trace
    if result.algorithm is AlgorithmKind.SIDEWAYS:
        sideways = [
            point
            for point in points
            if point.accepted is True and point.delta == 0
        ]
        return {
            "sideways_moves": len(sideways),
            "max_consecutive_sideways": max(
                (point.sideways_moves or 0 for point in points),
                default=0,
            ),
        }
    if result.algorithm is AlgorithmKind.STOCHASTIC:
        probabilities = [
            point.accept_prob
            for point in points
            if point.accept_prob is not None
        ]
        return {
            "uphill_moves_selected": sum(point.accepted is True for point in points),
            "mean_selection_probability": (
                fmean(probabilities) if probabilities else None
            ),
        }
    if result.algorithm is AlgorithmKind.RANDOM_RESTART:
        return _restart_metrics(result)
    if result.algorithm is AlgorithmKind.SIMULATED_ANNEALING:
        decisions = [point for point in points if point.accepted is not None]
        return {
            "accepted_moves": sum(point.accepted is True for point in decisions),
            "rejected_moves": sum(point.accepted is False for point in decisions),
            "downhill_moves_accepted": sum(
                point.accepted is True
                and point.delta is not None
                and point.delta < 0
                for point in decisions
            ),
            "stuck_episodes": sum(point.stuck is True for point in points),
            "final_temperature": next(
                (
                    point.temperature
                    for point in reversed(points)
                    if point.temperature is not None
                ),
                None,
            ),
        }
    if result.algorithm is AlgorithmKind.GENETIC_ALGORITHM:
        generation = max(
            (point.generation or 0 for point in points),
            default=0,
        )
        return {
            "generations_completed": generation,
            "final_population_mean": next(
                (
                    point.population_mean_objective
                    for point in reversed(points)
                    if point.population_mean_objective is not None
                ),
                None,
            ),
            "best_generation": next(
                (
                    point.generation
                    for point in points
                    if point.objective == result.best_objective
                ),
                None,
            ),
        }
    return {
        "improving_moves": sum(point.accepted is True for point in points),
    }


def build_run_metrics(
    problem: Problem,
    result: SearchResult,
    *,
    elapsed_seconds: float | None = None,
) -> dict[str, Any]:
    """Menyusun metrics run yang siap diserialisasi."""
    best = summarize_state(problem, result.best_state, result.objective)
    final = summarize_state(problem, result.final_state, result.objective)
    return {
        "algorithm": result.algorithm.value,
        "algorithm_name": ALGORITHM_NAMES[result.algorithm],
        "objective": result.objective.value,
        "seed": result.seed,
        "stopped_reason": result.stopped_reason.value,
        "iterations": iteration_count(result),
        "evaluations": result.evaluations_used,
        "elapsed_seconds": elapsed_seconds,
        "initial_objective": result.initial_objective,
        "final_objective": result.final_objective,
        "best_objective": result.best_objective,
        "best_total_value": best["total_value"],
        "best_urgency_score": best["urgency_score"],
        "inside_count": best["inside_count"],
        "outside_count": best["outside_count"],
        "trucks": best["trucks"],
        "final_summary": final,
        "algorithm_metrics": algorithm_metrics(result),
    }


__all__ = [
    "ALGORITHM_NAMES",
    "algorithm_metrics",
    "build_run_metrics",
    "iteration_count",
]
