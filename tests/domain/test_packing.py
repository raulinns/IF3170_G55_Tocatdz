import random

from if3170_tubes1.domain import (
    Dimensions,
    Orientation,
    Package,
    Placement,
    Position,
    Problem,
    State,
    Truck,
    build_random_state,
    candidate_anchors,
    try_place,
    validate_state,
)


def make_problem() -> Problem:
    return Problem(
        "packing",
        (Truck("T1", Dimensions(4, 3, 2), 5),),
        (
            Package("A", Dimensions(2, 2, 1), 5, 2, False, 0),
            Package("B", Dimensions(2, 1, 1), 4, 2, True, 1),
            Package("C", Dimensions(5, 5, 5), 100, 1, False, 0),
        ),
    )


def test_candidate_anchors_are_deduplicated_and_sorted_by_zyx() -> None:
    problem = make_problem()
    state = State(
        (
            Placement("A", "T1", Position(0, 0, 0)),
            Placement("B", "T1", Position(2, 0, 0)),
            Placement("C"),
        )
    )

    assert candidate_anchors(problem, state, "T1") == (
        Position(0, 0, 0),
        Position(2, 0, 0),
        Position(4, 0, 0),
        Position(2, 1, 0),
        Position(0, 2, 0),
        Position(0, 0, 1),
        Position(2, 0, 1),
    )


def test_try_place_rejects_invalid_candidate_without_mutating_state() -> None:
    problem = make_problem()
    state = State.all_outside(problem)

    assert try_place(problem, state, "A", "T1", Position(3, 0, 0), Orientation.WLH) is None
    placed = try_place(problem, state, "A", "T1", Position(0, 0, 0), Orientation.WLH)

    assert placed is not None
    assert state.placement("A").is_outside
    assert not placed.placement("A").is_outside


def test_moving_a_support_cannot_strand_packages_above_it() -> None:
    problem = make_problem()
    stacked = State(
        (
            Placement("A", "T1", Position(0, 0, 0)),
            Placement("B", "T1", Position(0, 0, 1)),
            Placement("C"),
        )
    )

    assert (
        try_place(problem, stacked, "A", None, None, Orientation.WLH)
        is None
    )


def test_random_construction_is_seeded_complete_and_feasible() -> None:
    problem = make_problem()

    first = build_random_state(problem, random.Random(42))
    second = build_random_state(problem, random.Random(42))

    assert first == second
    assert validate_state(problem, first).is_valid
    assert tuple(item.package_id for item in first.placements) == ("A", "B", "C")
    assert first.placement("C").is_outside
