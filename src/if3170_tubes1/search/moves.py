from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Literal, TypeAlias

from ..domain.constraints import validate_placement_changes
from ..domain.model import Orientation, Placement, Position, Problem, State
from ..domain.packing import candidate_anchors, try_place


@dataclass(frozen=True, slots=True)
class Relocate:
    package_id: str
    truck_id: str | None
    position: Position | None


@dataclass(frozen=True, slots=True)
class Swap:
    package_a: str
    package_b: str


@dataclass(frozen=True, slots=True)
class Rotate:
    package_id: str
    axis: Literal["x", "y", "z"]


Move: TypeAlias = Relocate | Swap | Rotate


def rotated_orientation(
    problem: Problem,
    placement: Placement,
    axis: Literal["x", "y", "z"],
) -> Orientation:
    package = problem.package(placement.package_id)
    current = package.dimensions.oriented(placement.orientation)
    target = {
        "x": (current.width, current.height, current.length),
        "y": (current.height, current.length, current.width),
        "z": (current.length, current.width, current.height),
    }[axis]
    for orientation in Orientation:
        dimensions = package.dimensions.oriented(orientation)
        if (dimensions.width, dimensions.length, dimensions.height) == target:
            return orientation
    raise AssertionError("rotation must map to one of the six orientations")


def iter_candidate_moves(problem: Problem, state: State) -> Iterator[Move]:
    for placement in state.placements:
        if not placement.is_outside:
            yield Relocate(placement.package_id, None, None)

        state_without_package = state.replace(
            Placement(placement.package_id, orientation=placement.orientation)
        )
        for truck in problem.trucks:
            for anchor in candidate_anchors(problem, state_without_package, truck.id):
                if placement.truck_id != truck.id or placement.position != anchor:
                    yield Relocate(placement.package_id, truck.id, anchor)

        current_dimensions = problem.package(placement.package_id).dimensions.oriented(
            placement.orientation
        )
        yielded_dimensions = {
            (
                current_dimensions.width,
                current_dimensions.length,
                current_dimensions.height,
            )
        }
        for axis in ("x", "y", "z"):
            orientation = rotated_orientation(problem, placement, axis)
            dimensions = problem.package(placement.package_id).dimensions.oriented(
                orientation
            )
            key = (dimensions.width, dimensions.length, dimensions.height)
            if key not in yielded_dimensions:
                yielded_dimensions.add(key)
                yield Rotate(placement.package_id, axis)

    package_ids = [placement.package_id for placement in state.placements]
    for index, package_a in enumerate(package_ids):
        for package_b in package_ids[index + 1 :]:
            yield Swap(package_a, package_b)


def apply_move(problem: Problem, state: State, move: Move) -> State | None:
    if isinstance(move, Relocate):
        placement = state.placement(move.package_id)
        return try_place(
            problem,
            state,
            move.package_id,
            move.truck_id,
            move.position,
            placement.orientation,
        )

    if isinstance(move, Rotate):
        placement = state.placement(move.package_id)
        return try_place(
            problem,
            state,
            move.package_id,
            placement.truck_id,
            placement.position,
            rotated_orientation(problem, placement, move.axis),
        )

    placement_a = state.placement(move.package_a)
    placement_b = state.placement(move.package_b)
    candidate = state.replace(
        Placement(
            placement_a.package_id,
            placement_b.truck_id,
            placement_b.position,
            placement_a.orientation,
        )
    ).replace(
        Placement(
            placement_b.package_id,
            placement_a.truck_id,
            placement_a.position,
            placement_b.orientation,
        )
    )
    if candidate == state:
        return None
    result = validate_placement_changes(
        problem,
        state,
        candidate,
        frozenset((move.package_a, move.package_b)),
    )
    return candidate if result.is_valid else None


def iter_feasible_neighbors(
    problem: Problem,
    state: State,
) -> Iterator[tuple[Move, State]]:
    for move in iter_candidate_moves(problem, state):
        successor = apply_move(problem, state, move)
        if successor is not None and successor != state:
            yield move, successor
