from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .model import Dimensions, Placement, Problem, State


@dataclass(frozen=True, slots=True)
class Violation:
    code: str
    message: str
    package_ids: tuple[str, ...] = ()
    truck_id: str | None = None


@dataclass(frozen=True, slots=True)
class ValidationResult:
    violations: tuple[Violation, ...]

    @property
    def is_valid(self) -> bool:
        return not self.violations

    def has(self, code: str) -> bool:
        return any(violation.code == code for violation in self.violations)


def _intervals_overlap(start_a: int, size_a: int, start_b: int, size_b: int) -> bool:
    return max(start_a, start_b) < min(start_a + size_a, start_b + size_b)


def footprints_overlap(
    placement_a: Placement,
    dimensions_a: Dimensions,
    placement_b: Placement,
    dimensions_b: Dimensions,
) -> bool:
    assert placement_a.position is not None and placement_b.position is not None
    return _intervals_overlap(
        placement_a.position.x,
        dimensions_a.width,
        placement_b.position.x,
        dimensions_b.width,
    ) and _intervals_overlap(
        placement_a.position.y,
        dimensions_a.length,
        placement_b.position.y,
        dimensions_b.length,
    )


def boxes_overlap(
    placement_a: Placement,
    dimensions_a: Dimensions,
    placement_b: Placement,
    dimensions_b: Dimensions,
) -> bool:
    assert placement_a.position is not None and placement_b.position is not None
    return footprints_overlap(
        placement_a,
        dimensions_a,
        placement_b,
        dimensions_b,
    ) and _intervals_overlap(
        placement_a.position.z,
        dimensions_a.height,
        placement_b.position.z,
        dimensions_b.height,
    )


def validate_state(problem: Problem, state: State) -> ValidationResult:
    violations: list[Violation] = []
    expected_ids = {package.id for package in problem.packages}
    placement_ids = [placement.package_id for placement in state.placements]
    id_counts = Counter(placement_ids)
    actual_ids = set(id_counts)

    missing = tuple(sorted(expected_ids - actual_ids))
    unknown = tuple(sorted(actual_ids - expected_ids))
    duplicates = tuple(sorted(item for item, count in id_counts.items() if count > 1))
    if missing:
        violations.append(Violation("missing_packages", "state omits packages", missing))
    if unknown:
        violations.append(Violation("unknown_packages", "state contains unknown packages", unknown))
    if duplicates:
        violations.append(Violation("duplicate_packages", "state repeats packages", duplicates))

    inside: list[tuple[Placement, Dimensions]] = []
    for placement in state.placements:
        if placement.package_id not in expected_ids:
            continue
        if placement.truck_id is None or placement.position is None:
            if placement.truck_id is not None or placement.position is not None:
                violations.append(
                    Violation(
                        "invalid_placement",
                        "truck and position must both be set or both be null",
                        (placement.package_id,),
                        placement.truck_id,
                    )
                )
            continue

        try:
            truck = problem.truck(placement.truck_id)
        except KeyError:
            violations.append(
                Violation(
                    "unknown_truck",
                    "placement refers to an unknown truck",
                    (placement.package_id,),
                    placement.truck_id,
                )
            )
            continue

        dimensions = problem.package(placement.package_id).dimensions.oriented(
            placement.orientation
        )
        position = placement.position
        if (
            min(position.x, position.y, position.z) < 0
            or position.x + dimensions.width > truck.dimensions.width
            or position.y + dimensions.length > truck.dimensions.length
            or position.z + dimensions.height > truck.dimensions.height
        ):
            violations.append(
                Violation(
                    "out_of_bounds",
                    "package exceeds truck bounds",
                    (placement.package_id,),
                    truck.id,
                )
            )
        inside.append((placement, dimensions))

    for index, (placement_a, dimensions_a) in enumerate(inside):
        for placement_b, dimensions_b in inside[index + 1 :]:
            if placement_a.truck_id == placement_b.truck_id and boxes_overlap(
                placement_a,
                dimensions_a,
                placement_b,
                dimensions_b,
            ):
                violations.append(
                    Violation(
                        "overlap",
                        "packages overlap",
                        (placement_a.package_id, placement_b.package_id),
                        placement_a.truck_id,
                    )
                )

    for truck in problem.trucks:
        package_ids = tuple(
            placement.package_id
            for placement, _ in inside
            if placement.truck_id == truck.id
        )
        weight = sum(problem.package(package_id).weight for package_id in package_ids)
        if weight > truck.max_capacity:
            violations.append(
                Violation(
                    "capacity_exceeded",
                    "truck weight capacity is exceeded",
                    package_ids,
                    truck.id,
                )
            )

    for upper, upper_dimensions in inside:
        assert upper.position is not None
        if upper.position.z == 0:
            continue
        supporters: list[Placement] = []
        for lower, lower_dimensions in inside:
            if lower.package_id == upper.package_id or lower.truck_id != upper.truck_id:
                continue
            assert lower.position is not None
            if (
                lower.position.z + lower_dimensions.height == upper.position.z
                and footprints_overlap(
                    upper,
                    upper_dimensions,
                    lower,
                    lower_dimensions,
                )
            ):
                supporters.append(lower)
        if not supporters:
            violations.append(
                Violation(
                    "floating",
                    "package has no positive-area support",
                    (upper.package_id,),
                    upper.truck_id,
                )
            )
        for supporter in supporters:
            if problem.package(supporter.package_id).is_fragile:
                violations.append(
                    Violation(
                        "fragile_support",
                        "a fragile package supports another package",
                        (supporter.package_id, upper.package_id),
                        upper.truck_id,
                    )
                )

    return ValidationResult(tuple(violations))


def validate_placement_changes(
    problem: Problem,
    before: State,
    after: State,
    changed_package_ids: frozenset[str],
) -> ValidationResult:
    """Validate a move from an already-valid state without rescanning unrelated pairs."""
    violations: list[Violation] = []
    changed = [after.placement(package_id) for package_id in changed_package_ids]
    affected_trucks = {
        truck_id
        for package_id in changed_package_ids
        for truck_id in (
            before.placement(package_id).truck_id,
            after.placement(package_id).truck_id,
        )
        if truck_id is not None
    }

    for placement in changed:
        if placement.is_outside:
            if placement.position is not None:
                violations.append(
                    Violation(
                        "invalid_placement",
                        "outside placement must have a null position",
                        (placement.package_id,),
                    )
                )
            continue
        if placement.position is None:
            violations.append(
                Violation(
                    "invalid_placement",
                    "inside placement must have a position",
                    (placement.package_id,),
                    placement.truck_id,
                )
            )
            continue
        truck = problem.truck(placement.truck_id)
        dimensions = problem.package(placement.package_id).dimensions.oriented(
            placement.orientation
        )
        position = placement.position
        if (
            min(position.x, position.y, position.z) < 0
            or position.x + dimensions.width > truck.dimensions.width
            or position.y + dimensions.length > truck.dimensions.length
            or position.z + dimensions.height > truck.dimensions.height
        ):
            violations.append(
                Violation(
                    "out_of_bounds",
                    "package exceeds truck bounds",
                    (placement.package_id,),
                    truck.id,
                )
            )

        for other in after.placements:
            if (
                other.package_id == placement.package_id
                or other.truck_id != placement.truck_id
                or other.position is None
            ):
                continue
            other_dimensions = problem.package(other.package_id).dimensions.oriented(
                other.orientation
            )
            if boxes_overlap(placement, dimensions, other, other_dimensions):
                pair = tuple(sorted((placement.package_id, other.package_id)))
                if not any(
                    violation.code == "overlap" and violation.package_ids == pair
                    for violation in violations
                ):
                    violations.append(
                        Violation("overlap", "packages overlap", pair, truck.id)
                    )

    for truck_id in affected_trucks:
        truck = problem.truck(truck_id)
        package_ids = tuple(
            placement.package_id
            for placement in after.placements
            if placement.truck_id == truck_id
        )
        weight = sum(problem.package(package_id).weight for package_id in package_ids)
        if weight > truck.max_capacity:
            violations.append(
                Violation(
                    "capacity_exceeded",
                    "truck weight capacity is exceeded",
                    package_ids,
                    truck_id,
                )
            )

    affected_upper_ids = set(changed_package_ids)
    for state in (before, after):
        for upper in state.placements:
            if upper.position is None or upper.position.z == 0:
                continue
            upper_dimensions = problem.package(upper.package_id).dimensions.oriented(
                upper.orientation
            )
            for lower_id in changed_package_ids:
                lower = state.placement(lower_id)
                if lower.truck_id != upper.truck_id or lower.position is None:
                    continue
                lower_dimensions = problem.package(lower_id).dimensions.oriented(
                    lower.orientation
                )
                if (
                    lower.position.z + lower_dimensions.height == upper.position.z
                    and footprints_overlap(
                        upper,
                        upper_dimensions,
                        lower,
                        lower_dimensions,
                    )
                ):
                    affected_upper_ids.add(upper.package_id)

    for upper_id in affected_upper_ids:
        upper = after.placement(upper_id)
        if upper.position is None or upper.position.z == 0:
            continue
        upper_dimensions = problem.package(upper_id).dimensions.oriented(
            upper.orientation
        )
        supporters: list[Placement] = []
        for lower in after.placements:
            if (
                lower.package_id == upper_id
                or lower.truck_id != upper.truck_id
                or lower.position is None
            ):
                continue
            lower_dimensions = problem.package(lower.package_id).dimensions.oriented(
                lower.orientation
            )
            if (
                lower.position.z + lower_dimensions.height == upper.position.z
                and footprints_overlap(
                    upper,
                    upper_dimensions,
                    lower,
                    lower_dimensions,
                )
            ):
                supporters.append(lower)
        if not supporters:
            violations.append(
                Violation(
                    "floating",
                    "package has no positive-area support",
                    (upper_id,),
                    upper.truck_id,
                )
            )
        for supporter in supporters:
            if problem.package(supporter.package_id).is_fragile:
                violations.append(
                    Violation(
                        "fragile_support",
                        "a fragile package supports another package",
                        (supporter.package_id, upper_id),
                        upper.truck_id,
                    )
                )

    return ValidationResult(tuple(violations))
