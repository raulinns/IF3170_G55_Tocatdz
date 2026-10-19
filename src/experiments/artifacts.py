from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    columns = list(dict.fromkeys(key for row in rows for key in row))
    if not columns:
        columns = ["status"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_chart(path: Path, rows: list[dict[str, Any]], metric: str, title: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    groups = [row for row in rows if row.get(f"{metric}_median") is not None]
    figure, axis = plt.subplots(figsize=(9, 4.8), constrained_layout=True)
    if groups:
        labels = [str(row["group_label"]) for row in groups]
        values = [float(row[f"{metric}_median"]) for row in groups]
        axis.bar(labels, values, color="#3969ac")
        axis.tick_params(axis="x", labelrotation=25)
    else:
        axis.text(0.5, 0.5, "Tidak ada run berhasil", ha="center", va="center")
        axis.set_xticks([])
    axis.set_title(title)
    axis.set_ylabel(metric.replace("_", " ").title())
    axis.grid(axis="y", alpha=0.25)
    figure.savefig(path, dpi=150)
    plt.close(figure)


def write_experiment_artifacts(
    experiment_dir: Path,
    manifest: dict[str, Any],
    runs: list[dict[str, Any]],
    summary: list[dict[str, Any]],
) -> None:
    experiment_dir.mkdir(parents=True, exist_ok=True)
    timestamp = str(manifest["experiment_id"])
    _write_csv(experiment_dir / f"{timestamp}-rekap.csv", summary)
    (experiment_dir / f"{timestamp}-rekap.json").write_text(
        json.dumps({"summary": summary, "runs": runs}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_chart(
        experiment_dir / f"{timestamp}-objective.png",
        summary,
        "best_objective",
        "Perbandingan objective (median)",
    )
    _write_chart(
        experiment_dir / f"{timestamp}-durasi.png",
        summary,
        "elapsed_seconds",
        "Perbandingan durasi (median)",
    )
    _write_chart(
        experiment_dir / f"{timestamp}-evaluasi.png",
        summary,
        "evaluations",
        "Perbandingan evaluasi (median)",
    )


__all__ = ["write_experiment_artifacts"]
