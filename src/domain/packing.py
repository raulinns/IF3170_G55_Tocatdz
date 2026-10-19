from __future__ import annotations

import random

from .constraints import validate_placement_changes
from .model import Orientation, Placement, Position, Problem, State


def candidate_anchors(problem: Problem, state: State, truck_id: str) -> tuple[Position, ...]:
    problem.truck(truck_id)
    anchors = {Position(0, 0, 0)}
    for placement in state.placements:
        if placement.truck_id != truck_id or placement.position is None:
            continue
        dimensions = problem.package(placement.package_id).dimensions.oriented(
            placement.orientation
        )
        position = placement.position
        anchors.update(
            (
                Position(position.x + dimensions.width, position.y, position.z),
                Position(position.x, position.y + dimensions.length, position.z),
                Position(position.x, position.y, position.z + dimensions.height),
            )
        )
    return tuple(sorted(anchors, key=lambda point: (point.z, point.y, point.x)))


def try_place(
    problem: Problem,
    state: State,
    package_id: str,
    truck_id: str | None,
    position: Position | None,
    orientation: Orientation,
) -> State | None:
    package = problem.package(package_id)
    if truck_id is None or position is None:
        if truck_id is not None or position is not None:
            return None
        candidate = state.replace(Placement(package_id, orientation=orientation))
        result = validate_placement_changes(
            problem,
            state,
            candidate,
            frozenset((package_id,)),
        )
        return candidate if result.is_valid else None

    truck = problem.truck(truck_id)
    dimensions = package.dimensions.oriented(orientation)
    if (
        min(position.x, position.y, position.z) < 0
        or position.x + dimensions.width > truck.dimensions.width
        or position.y + dimensions.length > truck.dimensions.length
        or position.z + dimensions.height > truck.dimensions.height
    ):
        return None
    current_weight = sum(
        problem.package(placement.package_id).weight
        for placement in state.placements
        if placement.truck_id == truck_id and placement.package_id != package_id
    )
    if current_weight + package.weight > truck.max_capacity:
        return None

    candidate = state.replace(Placement(package_id, truck_id, position, orientation))
    result = validate_placement_changes(
        problem,
        state,
        candidate,
        frozenset((package_id,)),
    )
    return candidate if result.is_valid else None


def build_random_state(problem: Problem, rng: random.Random) -> State:
    state = State.all_outside(problem)
    package_ids = [package.id for package in problem.packages]
    rng.shuffle(package_ids)

    for package_id in package_ids:
        trucks = list(problem.trucks)
        orientations = list(Orientation)
        rng.shuffle(trucks)
        rng.shuffle(orientations)
        placed: State | None = None
        for truck in trucks:
            anchors = list(candidate_anchors(problem, state, truck.id))
            rng.shuffle(anchors)
            for orientation in orientations:
                for anchor in anchors:
                    placed = try_place(
                        problem,
                        state,
                        package_id,
                        truck.id,
                        anchor,
                        orientation,
                    )
                    if placed is not None:
                        break
                if placed is not None:
                    break
            if placed is not None:
                break
        if placed is not None:
            state = placed

    return state
