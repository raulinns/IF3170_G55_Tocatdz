from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ...domain.model import Problem, State
from ...search.moves import iter_feasible_neighbors
from ...search.run import (
    AlgorithmKind,
    BudgetExhausted,
    RunCancelled,
    RunConfig,
    RunContext,
    SearchResult,
    StopReason,
    TracePoint,
)
from .common import (
    create_run_context,
    resolve_initial_state,
)


@dataclass(frozen=True, slots=True)
class _ClimbResult:
    state: State
    objective: float
    iterations: int
    stopped_reason: StopReason


def _run_steepest_climb(
    problem: Problem,
    context: RunContext,
    initial_state: State,
    initial_objective: float,
    *,
    restart: int | None = None,
) -> _ClimbResult:
    """Menjalankan satu climb steepest-ascent."""
    current = initial_state
    current_objective = initial_objective
    iterations = 0

    try:
        while True:
            context.check_cancelled()
            selected_state: State | None = None
            selected_objective = current_objective
            tie_count = 0

            for _, neighbor in iter_feasible_neighbors(problem, current):
                neighbor_objective = context.evaluate(neighbor)
                comparison = context.compare(
                    neighbor_objective,
                    selected_objective,
                )
                if comparison > 0:
                    selected_state = neighbor
                    selected_objective = neighbor_objective
                    tie_count = 1
                elif (
                    comparison == 0
                    and context.is_better(neighbor_objective, current_objective)
                ):
                    tie_count += 1
                    if context.rng.randrange(tie_count) == 0:
                        selected_state = neighbor

            if selected_state is None:
                return _ClimbResult(
                    current,
                    current_objective,
                    iterations,
                    StopReason.CONVERGED,
                )

            delta = selected_objective - current_objective
            current = selected_state
            current_objective = selected_objective
            iterations += 1
            context.record(
                current_objective,
                delta=delta,
                accepted=True,
                restart=restart,
                iteration_in_restart=iterations if restart is not None else None,
            )
    except BudgetExhausted:
        reason = StopReason.BUDGET_EXHAUSTED
    except RunCancelled:
        reason = StopReason.CANCELLED

    return _ClimbResult(current, current_objective, iterations, reason)


"""Menjalankan steepest-ascent pada seluruh feasible neighbor"""
def run_steepest_ascent(
    problem: Problem,
    config: RunConfig,
    *,
    initial_state: State | None = None,
    on_progress: Callable[[TracePoint], None] | None = None,
) -> SearchResult:
    if config.algorithm is not AlgorithmKind.STEEPEST_ASCENT:
        raise ValueError("run_steepest_ascent requires algorithm=steepest_ascent")

    context = create_run_context(problem, config, on_progress)
    initial = resolve_initial_state(problem, context, initial_state)
    initial_objective = context.evaluate(initial)
    context.record(initial_objective)
    climb = _run_steepest_climb(
        problem,
        context,
        initial,
        initial_objective,
    )

    return context.build_result(
        initial_state=initial,
        initial_objective=initial_objective,
        final_state=climb.state,
        final_objective=climb.objective,
        stopped_reason=climb.stopped_reason,
    )
