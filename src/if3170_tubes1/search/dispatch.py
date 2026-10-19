from __future__ import annotations

from collections.abc import Callable

from ..algorithms.hill_climbing import (
    run_random_restart,
    run_sideways,
    run_steepest_ascent,
    run_stochastic,
)
from ..algorithms.simulated_annealing import run_simulated_annealing
from ..algorithms.genetic_algorithm.gen_algorithm import run_genetic_algorithm
from ..domain.model import Problem
from .run import AlgorithmKind, RunConfig, SearchResult, TracePoint


ProgressCallback = Callable[[TracePoint], None]
Runner = Callable[..., SearchResult]

RUNNERS: dict[AlgorithmKind, Runner] = {
    AlgorithmKind.STEEPEST_ASCENT: run_steepest_ascent,
    AlgorithmKind.SIDEWAYS: run_sideways,
    AlgorithmKind.STOCHASTIC: run_stochastic,
    AlgorithmKind.RANDOM_RESTART: run_random_restart,
    AlgorithmKind.SIMULATED_ANNEALING: run_simulated_annealing,
    AlgorithmKind.GENETIC_ALGORITHM: run_genetic_algorithm,
}


def run_search(
    problem: Problem,
    config: RunConfig,
    *,
    on_progress: ProgressCallback | None = None,
) -> SearchResult:
    try:
        runner = RUNNERS[config.algorithm]
    except KeyError as error:
        raise NotImplementedError(
            f"runner {config.algorithm.value} is not integrated yet"
        ) from error
    return runner(problem, config, on_progress=on_progress)


__all__ = ["ProgressCallback", "RUNNERS", "Runner", "run_search"]
