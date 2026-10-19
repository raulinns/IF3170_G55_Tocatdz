from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..domain.model import Problem
from ..search.run import RunConfig, SearchResult


@dataclass(frozen=True, slots=True)
class CompletedRun:
    run_id: str
    started_at: str
    problem: Problem = field(compare=False, repr=False)
    config: RunConfig
    result: SearchResult
    elapsed_seconds: float
    metrics: dict[str, Any] = field(compare=False)
    artifact_dir: Path | None = field(default=None, compare=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "elapsed_seconds": self.elapsed_seconds,
            "artifact_dir": (
                None if self.artifact_dir is None else str(self.artifact_dir)
            ),
            "config": self.config.to_dict(),
            "metrics": self.metrics,
            "result": self.result.to_dict(),
        }


__all__ = ["CompletedRun"]
