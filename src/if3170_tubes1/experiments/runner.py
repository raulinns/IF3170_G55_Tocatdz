from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ..domain.constraints import validate_state
from ..execution.runner import execute_run
from ..io.problem_json import problem_to_data
from .aggregate import aggregate_runs
from .artifacts import write_experiment_artifacts
from .config import ExperimentConfig
from .protocols import ExperimentRunSpec, build_run_specs


RunExecutor = Callable[..., Any]
ProgressCallback = Callable[[int, int, ExperimentRunSpec, dict[str, Any]], None]


def _experiment_id() -> str:
    now = datetime.now(timezone.utc)
    return f"{now:%Y%m%dT%H%M%SZ}-{secrets.token_hex(4)}"


def _record_metrics(spec: ExperimentRunSpec, completed: Any, artifact_dir: Path) -> dict[str, Any]:
    metrics = completed.metrics
    algorithm_metrics = metrics.get("algorithm_metrics", {})
    return {
        "case_id": spec.case_id,
        "group_id": spec.group_id,
        "group_label": spec.group_label,
        "status": "success",
        "run_id": completed.run_id,
        "artifact_path": str(artifact_dir),
        "algorithm": completed.config.algorithm.value,
        "objective": completed.config.objective.value,
        "seed": completed.config.seed,
        "config_json": json.dumps(completed.config.to_dict(), sort_keys=True),
        "feasible": True,
        "stopped_reason": metrics.get("stopped_reason"),
        "best_objective": metrics.get("best_objective"),
        "best_total_value": metrics.get("best_total_value"),
        "best_urgency_score": metrics.get("best_urgency_score"),
        "evaluations": metrics.get("evaluations"),
        "iterations": metrics.get("iterations"),
        "elapsed_seconds": completed.elapsed_seconds,
        "sideways_moves": algorithm_metrics.get("sideways_moves"),
        "max_consecutive_sideways": algorithm_metrics.get("max_consecutive_sideways"),
        "stuck_episodes": algorithm_metrics.get("stuck_episodes"),
        "accepted_moves": algorithm_metrics.get("accepted_moves"),
        "rejected_moves": algorithm_metrics.get("rejected_moves"),
        "downhill_moves_accepted": algorithm_metrics.get("downhill_moves_accepted"),
        "uphill_moves_selected": algorithm_metrics.get("uphill_moves_selected"),
        "mean_selection_probability": algorithm_metrics.get("mean_selection_probability"),
        "restart_attempts": algorithm_metrics.get("attempts"),
        "restarts_completed": algorithm_metrics.get("restarts_completed"),
        "best_restart": algorithm_metrics.get("best_restart"),
        "generations_completed": algorithm_metrics.get("generations_completed"),
        "best_generation": algorithm_metrics.get("best_generation"),
        "final_population_mean": algorithm_metrics.get("final_population_mean"),
        "algorithm_metrics_json": json.dumps(algorithm_metrics, sort_keys=True),
        "error": "",
    }


def run_experiment(
    config: ExperimentConfig,
    *,
    executor: RunExecutor = execute_run,
    on_progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Run every case independently and keep successful run artifacts on failure."""
    specs = build_run_specs(config)
    experiment_id = _experiment_id()
    experiment_dir = (Path(config.output_root) / experiment_id).resolve()
    experiment_dir.mkdir(parents=True, exist_ok=False)
    run_artifact_root = experiment_dir / "run-artifacts"
    run_artifact_root.mkdir()
    records: list[dict[str, Any]] = []

    for spec in specs:
        try:
            completed = executor(config.problem, spec.config)
            for label, state in (
                ("initial", completed.result.initial_state),
                ("best", completed.result.best_state),
                ("final", completed.result.final_state),
            ):
                validation = validate_state(config.problem, state)
                if not validation.is_valid:
                    details = "; ".join(item.code for item in validation.violations)
                    raise ValueError(f"{label} state is infeasible: {details}")

            # Artifact generation happens after feasibility checks and is isolated per run.
            from ..execution.artifacts import write_run_artifacts

            artifact_dir = write_run_artifacts(completed, run_artifact_root)
            records.append(_record_metrics(spec, completed, artifact_dir))
        except Exception as error:
            records.append(
                {
                    "case_id": spec.case_id,
                    "group_id": spec.group_id,
                    "group_label": spec.group_label,
                    "status": "failed",
                    "run_id": "",
                    "artifact_path": "",
                    "algorithm": spec.config.algorithm.value,
                    "objective": spec.config.objective.value,
                    "seed": spec.config.seed,
                    "config_json": json.dumps(spec.config.to_dict(), sort_keys=True),
                    "feasible": False,
                    "error": f"{type(error).__name__}: {error}",
                }
            )
        if on_progress is not None:
            on_progress(len(records), len(specs), spec, records[-1])

    summary = aggregate_runs(records)
    successes = sum(record["status"] == "success" for record in records)
    manifest = {
        "experiment_id": experiment_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "protocol": config.protocol,
        "problem_name": config.problem.name,
        "problem": problem_to_data(config.problem),
        "objective": config.objective.value,
        "seeds": list(config.seeds),
        "max_evaluations": config.max_evaluations,
        "expected_runs": len(specs),
        "attempted_runs": len(records),
        "successful_runs": successes,
        "failed_runs": len(records) - successes,
        "note": "Hasil 3 seed bersifat deskriptif; bukan klaim signifikansi statistik.",
        "files": [
            "runs.csv",
            "summary.csv",
            "objective-comparison.png",
            "duration-comparison.png",
            "evaluation-comparison.png",
            "run-artifacts/",
        ],
    }
    write_experiment_artifacts(experiment_dir, manifest, records, summary)
    return {
        "experiment_id": experiment_id,
        "experiment_dir": experiment_dir,
        "expected_runs": len(specs),
        "successful_runs": successes,
        "failed_runs": len(records) - successes,
        "runs": records,
        "summary": summary,
    }


__all__ = ["ProgressCallback", "run_experiment"]
