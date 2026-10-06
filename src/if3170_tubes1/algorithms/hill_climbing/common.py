from __future__ import annotations

import random
from collections.abc import Callable

from ...domain.constraints import validate_state
from ...domain.model import Problem, State
from ...domain.packing import build_random_state
from ...search.run import RunConfig, RunContext, TracePoint


"""Membuat context pencarian"""
def create_run_context(
    problem: Problem,
    config: RunConfig,
    on_progress: Callable[[TracePoint], None] | None = None,
) -> RunContext:
    return RunContext(
        problem,
        config,
        rng=random.Random(config.seed),
        on_progress=on_progress,
    )


"""Membuat dan memvalidasi init state"""
def resolve_initial_state(
    problem: Problem,
    context: RunContext,
    initial_state: State | None,
) -> State:
    state = (
        build_random_state(problem, context.rng)
        if initial_state is None
        else initial_state
    )
    validation = validate_state(problem, state)
    if not validation.is_valid:
        codes = ", ".join(violation.code for violation in validation.violations)
        raise ValueError(f"initial_state must be feasible; violations: {codes}")
    return state
