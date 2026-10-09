from __future__ import annotations

import math
import random
from collections.abc import Callable, Iterator

from ..domain.constraints import validate_state
from ..domain.model import Problem, State
from ..domain.packing import build_random_state
from ..search.moves import iter_feasible_neighbors
from ..search.run import (
    AlgorithmKind,
    BudgetExhausted,
    RunCancelled,
    RunConfig,
    RunContext,
    SearchResult,
    StopReason,
    TracePoint,
)


def acceptance_probability(delta: float, temperature: float) -> float:
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    return 1.0 if delta >= 0 else math.exp(delta / temperature)


def _random_neighbor(
    problem: Problem, state: State, rng: random.Random
) -> State | None:
    selected = None
    for count, (_, neighbor) in enumerate(
        iter_feasible_neighbors(problem, state), start=1
    ):
        if rng.randrange(count) == 0:
            selected = neighbor
    return selected


def _negative_deltas(
    problem: Problem,
    state: State,
    current_objective: float,
    context: RunContext,
) -> Iterator[float]:
    for _, neighbor in iter_feasible_neighbors(problem, state):
        if not context.has_budget():
            return
        delta = context.evaluate(
            neighbor, track_best=False) - current_objective
        if delta < 0:
            yield abs(delta)


def _initial_temperature(
    problem: Problem,
    state: State,
    current_objective: float,
    context: RunContext,
) -> float:
    if context.config.calibration_samples == 0:
        return max(1.0, 10 * context.config.t_min)
    losses = []
    for loss in _negative_deltas(problem, state, current_objective, context):
        losses.append(loss)
        if len(losses) >= context.config.calibration_samples:
            break
    if not losses:
        return max(1.0, 10 * context.config.t_min)
    losses.sort()
    middle = len(losses) // 2
    median = (
        losses[middle]
        if len(losses) % 2
        else (losses[middle - 1] + losses[middle]) / 2
    )
    return max(-median / math.log(0.8), 10 * context.config.t_min)


def _is_local_optimum(
    problem: Problem, state: State, objective: float, context: RunContext
) -> bool:
    for _, neighbor in iter_feasible_neighbors(problem, state):
        if context.evaluate(neighbor, track_best=False) > objective:
            return False
    return True


def run_simulated_annealing(
    problem: Problem,
    config: RunConfig,
    *,
    initial_state: State | None = None,
    on_progress: Callable[[TracePoint], None] | None = None,
) -> SearchResult:
    if config.algorithm is not AlgorithmKind.SIMULATED_ANNEALING:
        raise ValueError(
            "run_simulated_annealing requires algorithm=simulated_annealing")

    context = RunContext(
        problem,
        config,
        rng=random.Random(config.seed),
        on_progress=on_progress
    )
    initial = build_random_state(
        problem, context.rng) if initial_state is None else initial_state
    validation = validate_state(problem, initial)
    if not validation.is_valid:
        codes = ", ".join(
            violation.code for violation in validation.violations)
        raise ValueError(
            f"initial_state must be feasible; violations: {codes}")

    current = initial
    current_objective = context.evaluate(current)
    initial_objective = current_objective
    context.record(current_objective)
    reason = StopReason.ITERATION_LIMIT

    try:
        if config.max_iterations == 0:
            return context.build_result(
                initial_state=initial,
                initial_objective=initial_objective,
                final_state=current,
                final_objective=current_objective,
                stopped_reason=reason,
            )

        temperature_0 = _initial_temperature(
            problem, current, current_objective, context
        )
        available_steps = min(
            config.max_iterations,
            max(1, config.max_evaluations - context.evaluations),
        )
        alpha = (config.t_min / temperature_0) ** (1 / available_steps)
        stuck_episode = False
        local_optimum_cache: dict[State, bool] = {}

        for iteration in range(config.max_iterations):
            context.check_cancelled()
            stuck = local_optimum_cache.get(current)
            if stuck is None:
                stuck = _is_local_optimum(
                    problem, current, current_objective, context
                )
                local_optimum_cache[current] = stuck

            neighbor = _random_neighbor(problem, current, context.rng)
            if neighbor is None:
                reason = StopReason.CONVERGED
                break

            neighbor_objective = context.evaluate(neighbor)
            delta = neighbor_objective - current_objective
            temperature = max(config.t_min, temperature_0 *
                              alpha ** (iteration + 1))
            probability = acceptance_probability(delta, temperature)
            random_draw = context.rng.random()
            accepted = random_draw < probability
            if accepted:
                current = neighbor
                current_objective = neighbor_objective

            context.record(
                current_objective,
                temperature=temperature,
                delta=delta,
                accept_prob=probability,
                random_draw=random_draw,
                accepted=accepted,
                stuck=stuck and not stuck_episode,
            )
            stuck_episode = stuck
        else:
            reason = StopReason.ITERATION_LIMIT
    except BudgetExhausted:
        reason = StopReason.BUDGET_EXHAUSTED
    except RunCancelled:
        reason = StopReason.CANCELLED

    return context.build_result(
        initial_state=initial,
        initial_objective=initial_objective,
        final_state=current,
        final_objective=current_objective,
        stopped_reason=reason,
    )
