from __future__ import annotations

from collections.abc import Callable

from domain.model import Problem, State
from search.moves import iter_feasible_neighbors
from search.run import (
    AlgorithmKind,
    BudgetExhausted,
    RunCancelled,
    RunConfig,
    SearchResult,
    StopReason,
    TracePoint,
)
from .common import create_run_context, resolve_initial_state


"""Menjalankan hill climbing dengan limit sideways move"""
def run_sideways(
    problem: Problem,
    config: RunConfig,
    *,
    initial_state: State | None = None,
    on_progress: Callable[[TracePoint], None] | None = None,
) -> SearchResult:
    if config.algorithm is not AlgorithmKind.SIDEWAYS:
        raise ValueError("run_sideways requires algorithm=sideways")

    context = create_run_context(problem, config, on_progress)
    initial = resolve_initial_state(problem, context, initial_state)
    initial_objective = context.evaluate(initial)
    current = initial
    current_objective = initial_objective
    sideways_moves = 0
    plateau_visited = {current}
    context.record(current_objective, sideways_moves=sideways_moves)
    stopped_reason = StopReason.CONVERGED

    try:
        while True:
            context.check_cancelled()
            improving_state: State | None = None
            improving_objective = current_objective
            improving_ties = 0
            sideways_state: State | None = None
            sideways_ties = 0

            for _, neighbor in iter_feasible_neighbors(problem, current):
                neighbor_objective = context.evaluate(neighbor)
                comparison = context.compare(
                    neighbor_objective,
                    improving_objective,
                )

                if comparison > 0:
                    improving_state = neighbor
                    improving_objective = neighbor_objective
                    improving_ties = 1
                elif (
                    comparison == 0
                    and context.is_better(neighbor_objective, current_objective)
                ):
                    improving_ties += 1
                    if context.rng.randrange(improving_ties) == 0:
                        improving_state = neighbor
                elif (
                    context.is_equal(neighbor_objective, current_objective)
                    and neighbor not in plateau_visited
                ):
                    sideways_ties += 1
                    if context.rng.randrange(sideways_ties) == 0:
                        sideways_state = neighbor

            if improving_state is not None:
                delta = improving_objective - current_objective
                current = improving_state
                current_objective = improving_objective
                sideways_moves = 0
                plateau_visited = {current}
                context.record(
                    current_objective,
                    delta=delta,
                    accepted=True,
                    sideways_moves=sideways_moves,
                )
                continue

            if sideways_state is None:
                break

            if config.max_sideways == 0:
                stopped_reason = StopReason.SIDEWAYS_LIMIT
                break

            current = sideways_state
            sideways_moves += 1
            plateau_visited.add(current)
            context.record(
                current_objective,
                delta=0.0,
                accepted=True,
                sideways_moves=sideways_moves,
            )

            if sideways_moves >= config.max_sideways:
                stopped_reason = StopReason.SIDEWAYS_LIMIT
                break
    except BudgetExhausted:
        stopped_reason = StopReason.BUDGET_EXHAUSTED
    except RunCancelled:
        stopped_reason = StopReason.CANCELLED

    return context.build_result(
        initial_state=initial,
        initial_objective=initial_objective,
        final_state=current,
        final_objective=current_objective,
        stopped_reason=stopped_reason,
    )
