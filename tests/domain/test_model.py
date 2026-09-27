import pytest

from if3170_tubes1.domain import (
    Dimensions,
    ObjectiveKind,
    Orientation,
    Package,
    Placement,
    Position,
    Problem,
    State,
    Truck,
)


def test_orientation_order_is_fixed() -> None:
    dimensions = Dimensions(1, 2, 3)

    assert [dimensions.oriented(orientation) for orientation in Orientation] == [
        Dimensions(1, 2, 3),
        Dimensions(1, 3, 2),
        Dimensions(2, 1, 3),
        Dimensions(2, 3, 1),
        Dimensions(3, 1, 2),
        Dimensions(3, 2, 1),
    ]


def test_problem_establishes_canonical_id_order_and_lookup() -> None:
    package_a = Package("A", Dimensions(1, 1, 1), 5, 1, False, 0)
    package_b = Package("B", Dimensions(2, 1, 1), 8, 2, True, 1)
    truck_a = Truck("T1", Dimensions(4, 4, 4), 10)
    truck_b = Truck("T2", Dimensions(5, 5, 5), 20)

    problem = Problem("fixture", (truck_b, truck_a), (package_b, package_a))

    assert tuple(truck.id for truck in problem.trucks) == ("T1", "T2")
    assert tuple(package.id for package in problem.packages) == ("A", "B")
    assert problem.truck("T2") is truck_b
    assert problem.package("A") is package_a


def test_duplicate_ids_are_rejected() -> None:
    truck = Truck("T1", Dimensions(4, 4, 4), 10)
    package = Package("P1", Dimensions(1, 1, 1), 5, 1, False, 0)

    with pytest.raises(ValueError, match="truck ids must be unique"):
        Problem("fixture", (truck, truck), (package,))

    with pytest.raises(ValueError, match="package ids must be unique"):
        Problem("fixture", (truck,), (package, package))


def test_state_starts_outside_and_replaces_without_reordering() -> None:
    packages = (
        Package("B", Dimensions(1, 1, 1), 2, 1, False, 0),
        Package("A", Dimensions(1, 1, 1), 1, 1, False, 0),
    )
    problem = Problem("fixture", (Truck("T1", Dimensions(2, 2, 2), 5),), packages)
    state = State.all_outside(problem)

    assert tuple(item.package_id for item in state.placements) == ("A", "B")
    assert all(item.is_outside for item in state.placements)

    replacement = Placement("B", "T1", Position(0, 0, 0), Orientation.LWH)
    changed = state.replace(replacement)

    assert changed.placement("B") == replacement
    assert tuple(item.package_id for item in changed.placements) == ("A", "B")
    assert state.placement("B").is_outside
    assert ObjectiveKind.TOTAL_VALUE == "total_value"


def test_state_canonicalizes_directly_supplied_placements() -> None:
    state = State((Placement("B"), Placement("A")))

    assert tuple(item.package_id for item in state.placements) == ("A", "B")
