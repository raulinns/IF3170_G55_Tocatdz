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


"""Menjalankan stochastic hill climbing pada uphill moves"""
def run_stochastic(
    problem: Problem,
    config: RunConfig,
    *,
    initial_state: State | None = None,
    on_progress: Callable[[TracePoint], None] | None = None,
) -> SearchResult:
    if config.algorithm is not AlgorithmKind.STOCHASTIC:
        raise ValueError("run_stochastic requires algorithm=stochastic")

    context = create_run_context(problem, config, on_progress)
    initial = resolve_initial_state(problem, context, initial_state)
    initial_objective = context.evaluate(initial)
    current = initial
    current_objective = initial_objective
    iterations = 0
    context.record(current_objective)
    stopped_reason = StopReason.CONVERGED

    try:
        while iterations < config.max_iterations:
            context.check_cancelled()
            uphill_moves: list[tuple[State, float, float]] = []

            for _, neighbor in iter_feasible_neighbors(problem, current):
                neighbor_objective = context.evaluate(neighbor)
                delta = neighbor_objective - current_objective
                if context.is_better(neighbor_objective, current_objective):
                    uphill_moves.append((neighbor, neighbor_objective, delta))

            if not uphill_moves:
                break

            weights = [delta for _, _, delta in uphill_moves]
            current, current_objective, delta = context.rng.choices(
                uphill_moves,
                weights=weights,
                k=1,
            )[0]
            probability = delta / sum(weights)
            iterations += 1
            context.record(
                current_objective,
                delta=delta,
                accept_prob=probability,
                accepted=True,
            )
        else:
            stopped_reason = StopReason.ITERATION_LIMIT
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
