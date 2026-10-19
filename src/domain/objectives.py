from __future__ import annotations

from .model import ObjectiveKind, Problem, State


def evaluate(problem: Problem, state: State, objective: ObjectiveKind) -> float:
    inside = (
        problem.package(placement.package_id)
        for placement in state.placements
        if not placement.is_outside
    )
    if objective is ObjectiveKind.TOTAL_VALUE:
        return sum(package.value for package in inside)
    return sum(package.value / (package.eta + 1) for package in inside)


def summarize_state(
    problem: Problem,
    state: State,
    active_objective: ObjectiveKind,
) -> dict[str, object]:
    truck_metrics: dict[str, dict[str, float | int]] = {}
    for truck in problem.trucks:
        packages = [
            problem.package(placement.package_id)
            for placement in state.placements
            if placement.truck_id == truck.id
        ]
        truck_metrics[truck.id] = {
            "weight": sum(package.weight for package in packages),
            "value": sum(package.value for package in packages),
            "package_count": len(packages),
        }

    inside_count = sum(not placement.is_outside for placement in state.placements)
    return {
        "objective": evaluate(problem, state, active_objective),
        "total_value": evaluate(problem, state, ObjectiveKind.TOTAL_VALUE),
        "urgency_score": evaluate(
            problem,
            state,
            ObjectiveKind.VALUE_PER_URGENCY,
        ),
        "inside_count": inside_count,
        "outside_count": len(state.placements) - inside_count,
        "trucks": truck_metrics,
    }
