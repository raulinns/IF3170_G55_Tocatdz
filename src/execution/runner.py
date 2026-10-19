from __future__ import annotations

import secrets
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from analysis.run_metrics import build_run_metrics
from domain.model import Problem
from search.dispatch import ProgressCallback, run_search
from search.run import RunConfig
from .artifacts import write_run_artifacts
from .model import CompletedRun


def _new_run_identity() -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    started_at = now.isoformat()
    run_id = f"{now:%Y%m%dT%H%M%S}-{secrets.token_hex(4)}"
    return run_id, started_at


def execute_run(
    problem: Problem,
    config: RunConfig,
    *,
    on_progress: ProgressCallback | None = None,
    artifact_root: str | Path | None = None,
) -> CompletedRun:
    """Menjalankan search dan menyiapkan metrics serta artefaknya."""
    run_id, started_at = _new_run_identity()
    started = perf_counter()
    result = run_search(problem, config, on_progress=on_progress)
    elapsed_seconds = perf_counter() - started
    metrics = build_run_metrics(
        problem,
        result,
        elapsed_seconds=elapsed_seconds,
    )
    completed = CompletedRun(
        run_id=run_id,
        started_at=started_at,
        problem=problem,
        config=config,
        result=result,
        elapsed_seconds=elapsed_seconds,
        metrics=metrics,
    )
    if artifact_root is not None:
        artifact_dir = write_run_artifacts(completed, artifact_root)
        completed = replace(completed, artifact_dir=artifact_dir)
    return completed


__all__ = ["execute_run"]
