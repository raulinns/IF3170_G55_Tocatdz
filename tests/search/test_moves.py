from if3170_tubes1.domain import (
    Dimensions,
    Orientation,
    Package,
    Placement,
    Position,
    Problem,
    State,
    Truck,
    validate_state,
)
from if3170_tubes1.search import (
    Relocate,
    Rotate,
    Swap,
    apply_move,
    iter_candidate_moves,
    iter_feasible_neighbors,
)


def make_problem() -> Problem:
    return Problem(
        "moves",
        (Truck("T1", Dimensions(4, 3, 3), 10),),
        (
            Package("A", Dimensions(2, 1, 1), 5, 2, False, 0),
            Package("B", Dimensions(2, 1, 1), 4, 2, False, 1),
        ),
    )


def test_relocate_rotate_and_swap_preserve_orientation_rules() -> None:
    problem = make_problem()
    state = State(
        (
            Placement("A", "T1", Position(0, 0, 0), Orientation.WLH),
            Placement("B"),
        )
    )

    inserted = apply_move(problem, state, Relocate("B", "T1", Position(2, 0, 0)))
    assert inserted is not None and not inserted.placement("B").is_outside

    rotated = apply_move(problem, state, Rotate("A", "z"))
    assert rotated is not None
    assert rotated.placement("A").orientation is Orientation.LWH

    swapped = apply_move(problem, state, Swap("A", "B"))
    assert swapped is not None
    assert swapped.placement("A").is_outside
    assert swapped.placement("B").position == Position(0, 0, 0)
    assert swapped.placement("B").orientation is Orientation.WLH


def test_candidate_moves_are_lazy_and_symmetric_rotations_are_deduplicated() -> None:
    problem = Problem(
        "symmetric",
        (Truck("T1", Dimensions(3, 3, 3), 10),),
        (
            Package("CUBE", Dimensions(1, 1, 1), 1, 1, False, 0),
            Package("RECT", Dimensions(2, 1, 1), 1, 1, False, 0),
        ),
    )
    state = State(
        (
            Placement("CUBE", orientation=Orientation.WHL),
            Placement("RECT"),
        )
    )
    moves = iter_candidate_moves(problem, state)

    assert iter(moves) is moves
    move_list = list(moves)
    assert not any(isinstance(move, Rotate) and move.package_id == "CUBE" for move in move_list)
    assert sum(isinstance(move, Swap) for move in move_list) == 1


def test_every_yielded_neighbor_is_feasible() -> None:
    problem = make_problem()
    state = State(
        (
            Placement("A", "T1", Position(0, 0, 0)),
            Placement("B"),
        )
    )
    neighbors = list(iter_feasible_neighbors(problem, state))

    assert neighbors
    assert all(validate_state(problem, successor).is_valid for _, successor in neighbors)
    assert all(successor != state for _, successor in neighbors)
