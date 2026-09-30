from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from ..domain.model import ObjectiveKind, Placement, Position, State
from ..domain.objectives import evaluate, summarize_state
from ..domain.model import Problem


class AlgorithmKind(StrEnum):
    STEEPEST_ASCENT = "steepest_ascent"
    SIDEWAYS = "sideways"
    STOCHASTIC = "stochastic"
    RANDOM_RESTART = "random_restart"
    SIMULATED_ANNEALING = "simulated_annealing"
    GENETIC_ALGORITHM = "genetic_algorithm"


class StopReason(StrEnum):
    CONVERGED = "converged"
    BUDGET_EXHAUSTED = "budget_exhausted"
    ITERATION_LIMIT = "iteration_limit"
    GENERATION_LIMIT = "generation_limit"
    RESTART_LIMIT = "restart_limit"
    CANCELLED = "cancelled"


DEFAULT_MAX_EVALUATIONS = 50_000
DEFAULT_SIDEWAYS_MAX = 100
DEFAULT_STOCHASTIC_ITERATIONS = 10_000
DEFAULT_RESTARTS = 10
DEFAULT_T_MIN = 0.001
DEFAULT_CALIBRATION_SAMPLES = 100
DEFAULT_POPULATION_SIZE = 50
DEFAULT_GENERATIONS = 100
DEFAULT_CROSSOVER_PROB = 0.9


class BudgetExhausted(RuntimeError):
    pass


class RunCancelled(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RunConfig:
    algorithm: AlgorithmKind = AlgorithmKind.STEEPEST_ASCENT
    objective: ObjectiveKind = ObjectiveKind.TOTAL_VALUE
    seed: int = 0
    max_evaluations: int = DEFAULT_MAX_EVALUATIONS
    max_sideways: int = DEFAULT_SIDEWAYS_MAX
    max_iterations: int = DEFAULT_STOCHASTIC_ITERATIONS
    num_restarts: int = DEFAULT_RESTARTS
    t_min: float = DEFAULT_T_MIN
    calibration_samples: int = DEFAULT_CALIBRATION_SAMPLES
    population_size: int = DEFAULT_POPULATION_SIZE
    generations: int = DEFAULT_GENERATIONS
    crossover_prob: float = DEFAULT_CROSSOVER_PROB
    mutation_prob: float | None = None

    def __post_init__(self) -> None:
        if self.max_evaluations <= 0:
            raise ValueError("max_evaluations must be positive")
        if self.max_sideways < 0:
            raise ValueError("max_sideways must be non-negative")
        if self.max_iterations < 0:
            raise ValueError("max_iterations must be non-negative")
        if self.num_restarts < 0:
            raise ValueError("num_restarts must be non-negative")
        if self.t_min <= 0:
            raise ValueError("t_min must be positive")
        if self.calibration_samples < 0:
            raise ValueError("calibration_samples must be non-negative")
        if self.population_size <= 0:
            raise ValueError("population_size must be positive")
        if self.generations <= 0:
            raise ValueError("generations must be positive")
        if not 0.0 <= self.crossover_prob <= 1.0:
            raise ValueError("crossover_prob must be in [0, 1]")
        if self.mutation_prob is not None and not 0.0 <= self.mutation_prob <= 1.0:
            raise ValueError("mutation_prob must be in [0, 1]")

    def mutation_rate(self, n_packages: int) -> float:
        if self.mutation_prob is not None:
            return self.mutation_prob
        return 1.0 / n_packages if n_packages > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "algorithm": self.algorithm.value,
            "objective": self.objective.value,
            "seed": self.seed,
            "max_evaluations": self.max_evaluations,
            "max_sideways": self.max_sideways,
            "max_iterations": self.max_iterations,
            "num_restarts": self.num_restarts,
            "t_min": self.t_min,
            "calibration_samples": self.calibration_samples,
            "population_size": self.population_size,
            "generations": self.generations,
            "crossover_prob": self.crossover_prob,
            "mutation_prob": self.mutation_prob,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RunConfig:
        return cls(
            algorithm=AlgorithmKind(data.get("algorithm", "steepest_ascent")),
            objective=ObjectiveKind(data.get("objective", "total_value")),
            seed=int(data.get("seed", 0)),
            max_evaluations=int(data.get("max_evaluations", DEFAULT_MAX_EVALUATIONS)),
            max_sideways=int(data.get("max_sideways", DEFAULT_SIDEWAYS_MAX)),
            max_iterations=int(
                data.get("max_iterations", DEFAULT_STOCHASTIC_ITERATIONS)
            ),
            num_restarts=int(data.get("num_restarts", DEFAULT_RESTARTS)),
            t_min=float(data.get("t_min", DEFAULT_T_MIN)),
            calibration_samples=int(
                data.get("calibration_samples", DEFAULT_CALIBRATION_SAMPLES)
            ),
            population_size=int(data.get("population_size", DEFAULT_POPULATION_SIZE)),
            generations=int(data.get("generations", DEFAULT_GENERATIONS)),
            crossover_prob=float(data.get("crossover_prob", DEFAULT_CROSSOVER_PROB)),
            mutation_prob=(
                None
                if data.get("mutation_prob") is None
                else float(data["mutation_prob"])
            ),
        )


@dataclass(frozen=True, slots=True)
class TracePoint:
    step: int
    evaluations: int
    objective: float
    best_objective: float
    temperature: float | None = None
    delta: float | None = None
    accept_prob: float | None = None
    random_draw: float | None = None
    accepted: bool | None = None
    generation: int | None = None
    stuck: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "evaluations": self.evaluations,
            "objective": self.objective,
            "best_objective": self.best_objective,
            "temperature": self.temperature,
            "delta": self.delta,
            "accept_prob": self.accept_prob,
            "random_draw": self.random_draw,
            "accepted": self.accepted,
            "generation": self.generation,
            "stuck": self.stuck,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> TracePoint:
        return cls(
            step=int(data["step"]),
            evaluations=int(data["evaluations"]),
            objective=float(data["objective"]),
            best_objective=float(data["best_objective"]),
            temperature=None
            if data.get("temperature") is None
            else float(data["temperature"]),
            delta=None if data.get("delta") is None else float(data["delta"]),
            accept_prob=None
            if data.get("accept_prob") is None
            else float(data["accept_prob"]),
            random_draw=None
            if data.get("random_draw") is None
            else float(data["random_draw"]),
            accepted=None if data.get("accepted") is None else bool(data["accepted"]),
            generation=None
            if data.get("generation") is None
            else int(data["generation"]),
            stuck=None if data.get("stuck") is None else bool(data["stuck"]),
        )


def state_to_dict(state: State) -> dict[str, Any]:
    placements = []
    for placement in state.placements:
        placements.append(
            {
                "package_id": placement.package_id,
                "truck_id": placement.truck_id,
                "position": None
                if placement.position is None
                else {
                    "x": placement.position.x,
                    "y": placement.position.y,
                    "z": placement.position.z,
                },
                "orientation": placement.orientation.value,
            }
        )
    return {"placements": placements}


def state_from_dict(data: Mapping[str, Any]) -> State:
    from ..domain.model import Orientation

    placements = []
    for item in data["placements"]:
        position = item["position"]
        placements.append(
            Placement(
                package_id=str(item["package_id"]),
                truck_id=item["truck_id"],
                position=None
                if position is None
                else Position(int(position["x"]), int(position["y"]), int(position["z"])),
                orientation=Orientation(int(item["orientation"])),
            )
        )
    return State(tuple(placements))


def child_seed(base_seed: int, index: int) -> int:
    return (base_seed + 7919 * (index + 1)) % (2**31)


@dataclass(frozen=True, slots=True)
class SearchResult:
    algorithm: AlgorithmKind
    objective: ObjectiveKind
    seed: int
    evaluations_used: int
    stopped_reason: StopReason
    initial_state: State
    initial_objective: float
    best_state: State
    best_objective: float
    final_state: State
    final_objective: float
    trace: tuple[TracePoint, ...] = ()
    config: RunConfig | None = field(default=None, compare=False)

    def summary(self, problem: Problem) -> dict[str, object]:
        return summarize_state(problem, self.best_state, self.objective)

    def trace_rows(self) -> list[dict[str, Any]]:
        return [point.to_dict() for point in self.trace]

    def to_dict(self) -> dict[str, Any]:
        return {
            "algorithm": self.algorithm.value,
            "objective": self.objective.value,
            "seed": self.seed,
            "evaluations_used": self.evaluations_used,
            "stopped_reason": self.stopped_reason.value,
            "initial_state": state_to_dict(self.initial_state),
            "initial_objective": self.initial_objective,
            "best_state": state_to_dict(self.best_state),
            "best_objective": self.best_objective,
            "final_state": state_to_dict(self.final_state),
            "final_objective": self.final_objective,
            "trace": [point.to_dict() for point in self.trace],
            "config": self.config.to_dict() if self.config is not None else None,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SearchResult:
        config = data.get("config")
        return cls(
            algorithm=AlgorithmKind(data["algorithm"]),
            objective=ObjectiveKind(data["objective"]),
            seed=int(data["seed"]),
            evaluations_used=int(data["evaluations_used"]),
            stopped_reason=StopReason(data["stopped_reason"]),
            initial_state=state_from_dict(data["initial_state"]),
            initial_objective=float(data["initial_objective"]),
            best_state=state_from_dict(data["best_state"]),
            best_objective=float(data["best_objective"]),
            final_state=state_from_dict(data["final_state"]),
            final_objective=float(data["final_objective"]),
            trace=tuple(TracePoint.from_dict(item) for item in data.get("trace", [])),
            config=None if config is None else RunConfig.from_dict(config),
        )


class RunContext:
    def __init__(
        self,
        problem: Problem,
        config: RunConfig,
        rng=None,
        on_progress: Callable[[TracePoint], None] | None = None,
    ) -> None:
        import random

        self.problem = problem
        self.config = config
        self.rng = rng if rng is not None else random.Random(config.seed)
        self.on_progress = on_progress
        self.evaluations = 0
        self.trace: list[TracePoint] = []
        self.best_state: State | None = None
        self.best_objective: float = float("-inf")
        self._cancelled = False
        self._step = 0

    def has_budget(self, needed: int = 1) -> bool:
        return self.evaluations + needed <= self.config.max_evaluations

    def check_budget(self, needed: int = 1) -> None:
        if not self.has_budget(needed):
            raise BudgetExhausted(
                f"evaluation budget exhausted: {self.evaluations}/{self.config.max_evaluations}"
            )

    def check_cancelled(self) -> None:
        if self._cancelled:
            raise RunCancelled("run was cancelled")

    def cancel(self) -> None:
        self._cancelled = True

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def compare(self, left: float, right: float) -> int:
        if left > right:
            return 1
        if left < right:
            return -1
        return 0

    def is_better(self, candidate: float, current: float) -> bool:
        return self.compare(candidate, current) > 0

    def is_equal(self, left: float, right: float) -> bool:
        return self.compare(left, right) == 0

    def argmax_tie(self, values: Sequence[float]):
        best = max(values)
        tied = [index for index, value in enumerate(values) if value == best]
        if len(tied) == 1:
            return tied[0]
        return self.rng.choice(tied)

    def evaluate(self, state: State) -> float:
        self.check_cancelled()
        self.check_budget(1)
        value = evaluate(self.problem, state, self.config.objective)
        self.evaluations += 1
        if value > self.best_objective:
            self.best_objective = value
            self.best_state = state
        return value

    def record(
        self,
        objective: float,
        *,
        temperature: float | None = None,
        delta: float | None = None,
        accept_prob: float | None = None,
        random_draw: float | None = None,
        accepted: bool | None = None,
        generation: int | None = None,
        stuck: bool | None = None,
    ) -> TracePoint:
        point = TracePoint(
            step=self._step,
            evaluations=self.evaluations,
            objective=objective,
            best_objective=self.best_objective,
            temperature=temperature,
            delta=delta,
            accept_prob=accept_prob,
            random_draw=random_draw,
            accepted=accepted,
            generation=generation,
            stuck=stuck,
        )
        self._step += 1
        self.trace.append(point)
        if self.on_progress is not None:
            self.on_progress(point)
        return point

    def build_result(
        self,
        *,
        initial_state: State,
        initial_objective: float,
        final_state: State,
        final_objective: float,
        stopped_reason: StopReason,
    ) -> SearchResult:
        assert self.best_state is not None, "no evaluation recorded"
        return SearchResult(
            algorithm=self.config.algorithm,
            objective=self.config.objective,
            seed=self.config.seed,
            evaluations_used=self.evaluations,
            stopped_reason=stopped_reason,
            initial_state=initial_state,
            initial_objective=initial_objective,
            best_state=self.best_state,
            best_objective=self.best_objective,
            final_state=final_state,
            final_objective=final_objective,
            trace=tuple(self.trace),
            config=self.config,
        )
