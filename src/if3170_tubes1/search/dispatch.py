from __future__ import annotations

from collections.abc import Callable

from ..algorithms.genetic_algorithm.gen_algorithm import run_genetic_algorithm
from ..domain.model import Problem
from .run import AlgorithmKind, RunConfig, SearchResult


Runner = Callable[[Problem, RunConfig], SearchResult]

# Register additional algorithms here when their runners are available.
RUNNERS: dict[AlgorithmKind, Runner] = {
    AlgorithmKind.GENETIC_ALGORITHM: run_genetic_algorithm,
}


def run_search(problem: Problem, config: RunConfig) -> SearchResult:
    try:
        runner = RUNNERS[config.algorithm]
    except KeyError as error:
        raise NotImplementedError(
            f"runner {config.algorithm.value} is not integrated yet"
        ) from error
    return runner(problem, config)
