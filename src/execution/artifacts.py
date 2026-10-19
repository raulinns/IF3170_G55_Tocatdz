from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Any

from problem_io.problem_json import problem_to_data
from search.run import state_to_dict
from .model import CompletedRun


TRACE_FIELDS = (
    "step",
    "evaluations",
    "objective",
    "best_objective",
    "temperature",
    "delta",
    "accept_prob",
    "random_draw",
    "accepted",
    "generation",
    "stuck",
    "population_mean_objective",
    "sideways_moves",
    "restart",
    "iteration_in_restart",
)


def _write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_trajectory(path: Path, run: CompletedRun) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TRACE_FIELDS)
        writer.writeheader()
        for row in run.result.trace_rows():
            writer.writerow({key: row.get(key) for key in TRACE_FIELDS})


def _write_objective_plot(path: Path, run: CompletedRun) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    points = run.result.trace
    x_values = [point.evaluations for point in points]
    current = [point.objective for point in points]
    best = [point.best_objective for point in points]
    if not points:
        x_values = [run.result.evaluations_used]
        current = [run.result.final_objective]
        best = [run.result.best_objective]

    figure, axis = plt.subplots(figsize=(8, 4.5), constrained_layout=True)
    axis.plot(x_values, current, marker="o", markersize=3, label="Current")
    axis.plot(x_values, best, linestyle="--", label="Best-so-far")
    axis.set_xlabel("Objective evaluations")
    axis.set_ylabel("Objective")
    axis.set_title(run.metrics["algorithm_name"])
    axis.grid(alpha=0.25)
    axis.legend()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def write_run_artifacts(
    run: CompletedRun,
    output_root: str | Path,
) -> Path:
    """Menulis artefak run secara atomik."""
    root = Path(output_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    final_dir = root / run.run_id
    temporary_dir = root / f".tmp-{run.run_id}"
    if final_dir.exists() or temporary_dir.exists():
        raise FileExistsError(f"artifact directory already exists for {run.run_id}")

    temporary_dir.mkdir()
    try:
        _write_json(temporary_dir / "problem.json", problem_to_data(run.problem))
        _write_json(
            temporary_dir / "initial-state.json",
            state_to_dict(run.result.initial_state),
        )
        _write_json(
            temporary_dir / "final-state.json",
            state_to_dict(run.result.final_state),
        )
        _write_json(
            temporary_dir / "best-state.json",
            state_to_dict(run.result.best_state),
        )
        _write_json(temporary_dir / "metrics.json", run.metrics)
        _write_trajectory(temporary_dir / "trajectory.csv", run)
        _write_objective_plot(temporary_dir / "objective.png", run)
        _write_json(
            temporary_dir / "manifest.json",
            {
                "run_id": run.run_id,
                "started_at": run.started_at,
                "elapsed_seconds": run.elapsed_seconds,
                "algorithm": run.config.algorithm.value,
                "objective": run.config.objective.value,
                "seed": run.config.seed,
                "config": run.config.to_dict(),
                "files": [
                    "problem.json",
                    "initial-state.json",
                    "final-state.json",
                    "best-state.json",
                    "trajectory.csv",
                    "metrics.json",
                    "objective.png",
                ],
            },
        )
        temporary_dir.replace(final_dir)
    except Exception:
        if temporary_dir.exists():
            shutil.rmtree(temporary_dir)
        raise
    return final_dir


__all__ = ["TRACE_FIELDS", "write_run_artifacts"]
