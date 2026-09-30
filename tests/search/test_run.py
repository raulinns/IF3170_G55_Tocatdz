import random

from if3170_tubes1.domain import (
    Dimensions,
    ObjectiveKind,
    Package,
    Placement,
    Position,
    Problem,
    State,
    Truck,
    validate_state,
)
from if3170_tubes1.search import (
    AlgorithmKind,
    BudgetExhausted,
    RunCancelled,
    RunConfig,
    RunContext,
    SearchResult,
    StopReason,
    TracePoint,
    child_seed,
)


def make_problem() -> Problem:
    return Problem(
        "run",
        (Truck("T1", Dimensions(3, 3, 3), 10),),
        (
            Package("A", Dimensions(1, 1, 1), 5, 1, False, 0),
            Package("B", Dimensions(1, 1, 1), 4, 1, False, 1),
        ),
    )


def make_state() -> State:
    return State(
        (
            Placement("A", "T1", Position(0, 0, 0)),
            Placement("B"),
        )
    )


def test_budget_gate_uses_one_shared_evaluation_definition() -> None:
    problem = make_problem()
    config = RunConfig(
        algorithm=AlgorithmKind.STEEPEST_ASCENT, max_evaluations=2, seed=7
    )
    ctx = RunContext(problem, config, random.Random(config.seed))
    state = make_state()

    ctx.check_budget()
    ctx.evaluate(state)
    ctx.evaluate(state)
    assert ctx.evaluations == 2
    assert not ctx.has_budget()
    try:
        ctx.evaluate(state)
    except BudgetExhausted:
        pass
    else:
        raise AssertionError("budget must stop new evaluations")


def test_best_tracking_and_seeded_tie_break_are_deterministic() -> None:
    problem = make_problem()
    config = RunConfig(algorithm=AlgorithmKind.STEEPEST_ASCENT, seed=3)
    first = RunContext(problem, config, random.Random(3)).argmax_tie([1.0, 1.0, 0.0])
    second = RunContext(problem, config, random.Random(3)).argmax_tie([1.0, 1.0, 0.0])
    assert first == second

    ctx = RunContext(problem, config, random.Random(3))
    low = make_state()
    high = State(
        (
            Placement("A", "T1", Position(0, 0, 0)),
            Placement("B", "T1", Position(1, 0, 0)),
        )
    )
    low_value = ctx.evaluate(low)
    high_value = ctx.evaluate(high)
    assert ctx.best_objective == max(low_value, high_value)
    assert ctx.best_state == (high if high_value >= low_value else low)


def test_cancel_boundary_and_result_round_trip() -> None:
    problem = make_problem()
    state = make_state()
    assert validate_state(problem, state).is_valid

    config = RunConfig(algorithm=AlgorithmKind.SIMULATED_ANNEALING, seed=1)
    ctx = RunContext(problem, config, random.Random(1))
    initial_value = ctx.evaluate(state)
    ctx.record(initial_value)
    ctx.cancel()
    assert ctx.cancelled
    try:
        ctx.evaluate(state)
    except RunCancelled:
        pass
    else:
        raise AssertionError("cancel must stop new evaluations")

    result = ctx.build_result(
        initial_state=state,
        initial_objective=initial_value,
        final_state=state,
        final_objective=initial_value,
        stopped_reason=StopReason.CANCELLED,
    )
    assert isinstance(result.trace[0], TracePoint)
    restored = SearchResult.from_dict(result.to_dict())
    assert restored == result
    assert restored.trace_rows()[0]["evaluations"] == 1
    assert child_seed(42, 0) != child_seed(42, 1)
