from if3170_tubes1.domain import (
    Dimensions,
    ObjectiveKind,
    Package,
    Placement,
    Position,
    Problem,
    State,
    Truck,
    evaluate,
    summarize_state,
)


def test_objectives_and_summary_only_count_inside_packages() -> None:
    problem = Problem(
        "objectives",
        (Truck("T1", Dimensions(3, 3, 3), 10),),
        (
            Package("A", Dimensions(1, 1, 1), 10, 2, False, 0),
            Package("B", Dimensions(1, 1, 1), 12, 3, False, 2),
            Package("C", Dimensions(1, 1, 1), 100, 1, False, 0),
        ),
    )
    state = State(
        (
            Placement("A", "T1", Position(0, 0, 0)),
            Placement("B", "T1", Position(1, 0, 0)),
            Placement("C"),
        )
    )

    assert evaluate(problem, state, ObjectiveKind.TOTAL_VALUE) == 22
    assert evaluate(problem, state, ObjectiveKind.VALUE_PER_URGENCY) == 14
    assert summarize_state(problem, state, ObjectiveKind.VALUE_PER_URGENCY) == {
        "objective": 14,
        "total_value": 22,
        "urgency_score": 14,
        "inside_count": 2,
        "outside_count": 1,
        "trucks": {"T1": {"weight": 5, "value": 22, "package_count": 2}},
    }
