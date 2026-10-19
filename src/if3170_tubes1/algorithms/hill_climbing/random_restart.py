from __future__ import annotations

import random
from collections.abc import Callable

from ...domain.model import Problem, State
from ...search.run import (
    AlgorithmKind,
    RunConfig,
    SearchResult,
    StopReason,
    TracePoint,
    child_seed,
)
from .common import create_run_context, resolve_initial_state
from .steepest_ascent import _run_steepest_climb


def run_random_restart(
    problem: Problem,
    config: RunConfig,
    *,
    initial_state: State | None = None,
    on_progress: Callable[[TracePoint], None] | None = None,
) -> SearchResult:
    """Menjalankan steepest-ascent dari beberapa initial state."""
    if config.algorithm is not AlgorithmKind.RANDOM_RESTART:
        raise ValueError("run_random_restart requires algorithm=random_restart")

    context = create_run_context(problem, config, on_progress)
    first_initial: State | None = None
    first_objective = 0.0
    stopped_reason = StopReason.RESTART_LIMIT

    for restart in range(config.num_restarts + 1):
        if not context.has_budget():
            stopped_reason = StopReason.BUDGET_EXHAUSTED
            break

        context.rng = random.Random(child_seed(config.seed, restart))
        restart_initial = resolve_initial_state(
            problem,
            context,
            initial_state if restart == 0 else None,
        )
        restart_objective = context.evaluate(restart_initial)

        if first_initial is None:
            first_initial = restart_initial
            first_objective = restart_objective

        context.record(
            restart_objective,
            restart=restart,
            iteration_in_restart=0,
        )
        climb = _run_steepest_climb(
            problem,
            context,
            restart_initial,
            restart_objective,
            restart=restart,
        )

        if climb.stopped_reason is not StopReason.CONVERGED:
            stopped_reason = climb.stopped_reason
            break

    assert first_initial is not None
    assert context.best_state is not None
    return context.build_result(
        initial_state=first_initial,
        initial_objective=first_objective,
        final_state=context.best_state,
        final_objective=context.best_objective,
        stopped_reason=stopped_reason,
    )
