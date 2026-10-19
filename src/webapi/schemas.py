from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from domain.model import ObjectiveKind
from search.run import (
    DEFAULT_CALIBRATION_SAMPLES,
    DEFAULT_CROSSOVER_PROB,
    DEFAULT_GENERATIONS,
    DEFAULT_MAX_EVALUATIONS,
    DEFAULT_POPULATION_SIZE,
    DEFAULT_RESTARTS,
    DEFAULT_SIDEWAYS_MAX,
    DEFAULT_STOCHASTIC_ITERATIONS,
    DEFAULT_T_MIN,
    AlgorithmKind,
    RunConfig,
)


class RunConfigInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    algorithm: AlgorithmKind = AlgorithmKind.STEEPEST_ASCENT
    objective: ObjectiveKind = ObjectiveKind.TOTAL_VALUE
    seed: int = 42
    max_evaluations: int = Field(default=DEFAULT_MAX_EVALUATIONS, gt=0)
    max_sideways: int = Field(default=DEFAULT_SIDEWAYS_MAX, ge=0)
    max_iterations: int = Field(default=DEFAULT_STOCHASTIC_ITERATIONS, ge=0)
    num_restarts: int = Field(default=DEFAULT_RESTARTS, ge=0)
    t_min: float = Field(default=DEFAULT_T_MIN, gt=0, allow_inf_nan=False)
    calibration_samples: int = Field(default=DEFAULT_CALIBRATION_SAMPLES, ge=0)
    population_size: int = Field(default=DEFAULT_POPULATION_SIZE, gt=0)
    generations: int = Field(default=DEFAULT_GENERATIONS, gt=0)
    crossover_prob: float = Field(default=DEFAULT_CROSSOVER_PROB, ge=0, le=1)
    mutation_prob: float | None = Field(default=None, ge=0, le=1)

    def to_domain(self) -> RunConfig:
        return RunConfig.from_dict(self.model_dump())


class PreviewRequest(BaseModel):
    problem: dict[str, Any]
    seed: int = 42
    objective: ObjectiveKind = ObjectiveKind.TOTAL_VALUE


class RunRequest(BaseModel):
    problem: dict[str, Any]
    config: RunConfigInput
    persist_artifacts: bool = True


class ReferenceRequest(BaseModel):
    problem: dict[str, Any]
    objective: ObjectiveKind = ObjectiveKind.TOTAL_VALUE
    candidate_value: float | None = None


class ExperimentRequest(BaseModel):
    problem: dict[str, Any]
    protocol: str
    objective: ObjectiveKind = ObjectiveKind.TOTAL_VALUE
    seeds: list[int] = Field(default_factory=lambda: [42, 137, 2026], min_length=1)
    max_evaluations: int = Field(default=DEFAULT_MAX_EVALUATIONS, gt=0)
    population_size: int = Field(default=DEFAULT_POPULATION_SIZE, gt=0)
    generations: int = Field(default=DEFAULT_GENERATIONS, gt=0)


__all__ = [
    "ExperimentRequest",
    "PreviewRequest",
    "ReferenceRequest",
    "RunConfigInput",
    "RunRequest",
]
