from __future__ import annotations

from collections import defaultdict
from statistics import median
from typing import Any


SUMMARY_METRICS = (
    "best_objective",
    "best_total_value",
    "best_urgency_score",
    "evaluations",
    "iterations",
    "elapsed_seconds",
    "sideways_moves",
    "max_consecutive_sideways",
    "stuck_episodes",
    "accepted_moves",
    "rejected_moves",
    "downhill_moves_accepted",
    "uphill_moves_selected",
    "mean_selection_probability",
    "restart_attempts",
    "restarts_completed",
    "best_restart",
    "generations_completed",
    "best_generation",
    "final_population_mean",
)


def aggregate_runs(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Summarize each protocol group while retaining source run IDs."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        groups[run["group_id"]].append(run)

    summaries = []
    for group_id, group in sorted(groups.items()):
        successful = [run for run in group if run["status"] == "success"]
        row: dict[str, Any] = {
            "group_id": group_id,
            "group_label": group[0]["group_label"],
            "run_count": len(group),
            "success_count": len(successful),
            "failure_count": len(group) - len(successful),
            "run_ids": ";".join(run["run_id"] for run in successful),
        }
        for metric in SUMMARY_METRICS:
            values = [run[metric] for run in successful if run.get(metric) is not None]
            row[f"{metric}_min"] = min(values) if values else None
            row[f"{metric}_median"] = median(values) if values else None
            row[f"{metric}_max"] = max(values) if values else None
        # Binary consistency is descriptive: it only reports whether all seeds agree.
        if successful:
            values = [run.get("best_objective") for run in successful]
            row["objective_consistent"] = len(set(values)) == 1
            reasons = sorted({run.get("stopped_reason", "") for run in successful})
            row["stop_reasons"] = ";".join(reasons)
            row["sideways_behavior"] = ";".join(
                f"{run['seed']}:{run.get('sideways_moves')}"
                for run in successful
                if run.get("sideways_moves") is not None
            )
            row["restart_behavior"] = ";".join(
                f"{run['seed']}:{run.get('restarts_completed')}"
                for run in successful
                if run.get("restarts_completed") is not None
            )
        else:
            row["objective_consistent"] = None
            row["stop_reasons"] = ""
            row["sideways_behavior"] = ""
            row["restart_behavior"] = ""
        summaries.append(row)
    return summaries


__all__ = ["SUMMARY_METRICS", "aggregate_runs"]
