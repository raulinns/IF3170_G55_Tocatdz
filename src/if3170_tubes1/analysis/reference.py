from __future__ import annotations

from dataclasses import dataclass

from ..domain.constraints import boxes_overlap, validate_state
from ..domain.model import ObjectiveKind, Orientation, Placement, Position, Problem, State
from ..domain.objectives import evaluate


@dataclass(frozen=True, slots=True)
class ExactReference:
    objective: ObjectiveKind
    value: float
    state: State
    nodes_explored: int


def _package_gain(problem: Problem, package_id: str, objective: ObjectiveKind) -> float:
    package = problem.package(package_id)
    if objective is ObjectiveKind.TOTAL_VALUE:
        return package.value
    return package.value / (package.eta + 1)


def solve_tiny_exact(
    problem: Problem,
    objective: ObjectiveKind = ObjectiveKind.TOTAL_VALUE,
) -> ExactReference:
    """Find an exact feasible packing for problems with at most six packages."""
    if len(problem.packages) > 6:
        raise ValueError("exact reference is limited to six packages")

    ordered_packages = sorted(
        problem.packages,
        key=lambda package: (
            -_package_gain(problem, package.id, objective),
            -(package.dimensions.width * package.dimensions.length * package.dimensions.height),
            package.id,
        ),
    )
    gains = [_package_gain(problem, package.id, objective) for package in ordered_packages]
    remaining_gain = [0.0] * (len(gains) + 1)
    for index in range(len(gains) - 1, -1, -1):
        remaining_gain[index] = remaining_gain[index + 1] + gains[index]

    best_state = State.all_outside(problem)
    best_value = evaluate(problem, best_state, objective)
    placements = best_state
    truck_weights = {truck.id: 0.0 for truck in problem.trucks}
    nodes_explored = 0

    def visit(index: int, current_value: float) -> None:
        nonlocal best_state, best_value, nodes_explored, placements
        nodes_explored += 1
        if current_value + remaining_gain[index] <= best_value + 1e-12:
            return
        if index == len(ordered_packages):
            if validate_state(problem, placements).is_valid and current_value > best_value:
                best_value = current_value
                best_state = placements
            return

        package = ordered_packages[index]
        for truck in problem.trucks:
            if truck_weights[truck.id] + package.weight > truck.max_capacity:
                continue
            seen_dimensions: set[tuple[int, int, int]] = set()
            for orientation in Orientation:
                dimensions = package.dimensions.oriented(orientation)
                dimension_key = (dimensions.width, dimensions.length, dimensions.height)
                if dimension_key in seen_dimensions:
                    continue
                seen_dimensions.add(dimension_key)
                if (
                    dimensions.width > truck.dimensions.width
                    or dimensions.length > truck.dimensions.length
                    or dimensions.height > truck.dimensions.height
                ):
                    continue
                for z in range(truck.dimensions.height - dimensions.height + 1):
                    for y in range(truck.dimensions.length - dimensions.length + 1):
                        for x in range(truck.dimensions.width - dimensions.width + 1):
                            placement = Placement(
                                package.id,
                                truck.id,
                                Position(x, y, z),
                                orientation,
                            )
                            if any(
                                other.truck_id == truck.id
                                and other.position is not None
                                and boxes_overlap(
                                    placement,
                                    dimensions,
                                    other,
                                    problem.package(other.package_id).dimensions.oriented(
                                        other.orientation
                                    ),
                                )
                                for other in placements.placements
                            ):
                                continue
                            placements = placements.replace(placement)
                            truck_weights[truck.id] += package.weight
                            visit(index + 1, current_value + gains[index])
                            truck_weights[truck.id] -= package.weight
                            placements = placements.replace(Placement(package.id))

        visit(index + 1, current_value)

    visit(0, 0.0)
    return ExactReference(objective, best_value, best_state, nodes_explored)


def knapsack_upper_bound(
    problem: Problem,
    objective: ObjectiveKind = ObjectiveKind.TOTAL_VALUE,
) -> float:
    """Exact 0/1 knapsack optimum using total fleet capacity as a relaxation."""
    capacity = sum(truck.max_capacity for truck in problem.trucks)
    items = [
        (package.weight, _package_gain(problem, package.id, objective))
        for package in problem.packages
        if package.weight <= capacity
    ]
    items.sort(
        key=lambda item: (
            -(item[1] / item[0] if item[0] > 0 else float("inf")),
            -item[1],
        )
    )
    suffix_gain = [0.0] * (len(items) + 1)
    for index in range(len(items) - 1, -1, -1):
        suffix_gain[index] = suffix_gain[index + 1] + items[index][1]

    best = 0.0

    def visit(index: int, used_weight: float, value: float) -> None:
        nonlocal best
        if value + suffix_gain[index] <= best + 1e-12:
            return
        if index == len(items):
            best = max(best, value)
            return
        weight, gain = items[index]
        if used_weight + weight <= capacity:
            visit(index + 1, used_weight + weight, value + gain)
        visit(index + 1, used_weight, value)

    visit(0, 0.0, 0.0)
    return best


__all__ = ["ExactReference", "knapsack_upper_bound", "solve_tiny_exact"]
