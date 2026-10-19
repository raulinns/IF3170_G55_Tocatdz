from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..domain.model import ObjectiveKind, Problem


DEFAULT_SEEDS = (42, 137, 2026)
DEFAULT_MAX_EVALUATIONS = 50_000


@dataclass(frozen=True, slots=True)
class ExperimentConfig:
    protocol: str
    problem: Problem = field(repr=False, compare=False)
    output_root: Path = Path("output/experiments")
    objective: ObjectiveKind = ObjectiveKind.TOTAL_VALUE
    seeds: tuple[int, ...] = DEFAULT_SEEDS
    max_evaluations: int = DEFAULT_MAX_EVALUATIONS

    def __post_init__(self) -> None:
        if not self.protocol.strip():
            raise ValueError("protocol must not be blank")
        if not self.seeds:
            raise ValueError("at least one seed is required")
        if self.max_evaluations <= 0:
            raise ValueError("max_evaluations must be positive")


__all__ = ["DEFAULT_MAX_EVALUATIONS", "DEFAULT_SEEDS", "ExperimentConfig"]
