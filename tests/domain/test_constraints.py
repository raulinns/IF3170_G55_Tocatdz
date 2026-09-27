from if3170_tubes1.domain import (
    Dimensions,
    Package,
    Placement,
    Position,
    Problem,
    State,
    Truck,
    validate_state,
)


def make_problem(*, fragile_base: bool = False, capacity: float = 10) -> Problem:
    return Problem(
        "constraints",
        (Truck("T1", Dimensions(4, 4, 4), capacity),),
        (
            Package("A", Dimensions(2, 2, 1), 5, 2, fragile_base, 0),
            Package("B", Dimensions(2, 2, 1), 8, 2, False, 1),
        ),
    )


def test_boundary_contact_is_not_overlap_and_one_cell_support_is_valid() -> None:
    problem = make_problem()
    side_by_side = State(
        (
            Placement("A", "T1", Position(0, 0, 0)),
            Placement("B", "T1", Position(2, 0, 0)),
        )
    )
    one_cell_support = State(
        (
            Placement("A", "T1", Position(0, 0, 0)),
            Placement("B", "T1", Position(1, 1, 1)),
        )
    )

    assert validate_state(problem, side_by_side).is_valid
    assert validate_state(problem, one_cell_support).is_valid


def test_corner_contact_is_floating_and_fragile_cannot_support() -> None:
    corner_problem = make_problem()
    corner_contact = State(
        (
            Placement("A", "T1", Position(0, 0, 0)),
            Placement("B", "T1", Position(2, 2, 1)),
        )
    )
    assert validate_state(corner_problem, corner_contact).has("floating")

    fragile_problem = make_problem(fragile_base=True)
    stacked = State(
        (
            Placement("A", "T1", Position(0, 0, 0)),
            Placement("B", "T1", Position(0, 0, 1)),
        )
    )
    assert validate_state(fragile_problem, stacked).has("fragile_support")


def test_overlap_bounds_capacity_and_placement_shape_are_rejected() -> None:
    problem = make_problem(capacity=3)
    invalid = State(
        (
            Placement("A", "T1", Position(3, 0, 0)),
            Placement("B", "T1", Position(3, 0, 0)),
        )
    )
    result = validate_state(problem, invalid)
    assert result.has("out_of_bounds")
    assert result.has("overlap")
    assert result.has("capacity_exceeded")

    malformed = State((Placement("A", "T1", None), Placement("B")))
    assert validate_state(problem, malformed).has("invalid_placement")


def test_package_coverage_is_reported_structurally() -> None:
    problem = make_problem()
    result = validate_state(
        problem,
        State((Placement("A"), Placement("A"), Placement("UNKNOWN"))),
    )

    assert result.has("missing_packages")
    assert result.has("unknown_packages")
    assert result.has("duplicate_packages")
