from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Any

from problem_io.problem_json import problem_to_data
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


def _box_faces(x: float, y: float, z: float, width: float, length: float, height: float):
    points = (
        (x, y, z), (x + width, y, z), (x + width, y + length, z), (x, y + length, z),
        (x, y, z + height), (x + width, y, z + height),
        (x + width, y + length, z + height), (x, y + length, z + height),
    )
    return (
        (points[0], points[1], points[2], points[3]),
        (points[4], points[5], points[6], points[7]),
        (points[0], points[1], points[5], points[4]),
        (points[2], points[3], points[7], points[6]),
        (points[1], points[2], points[6], points[5]),
        (points[0], points[3], points[7], points[4]),
    )


def _write_3d_viewer(path: Path, run: CompletedRun) -> None:
    """Simpan snapshot solusi terbaik dengan koordinat lokal per truk."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    figure = plt.figure(figsize=(11, 6.5), constrained_layout=True)
    axis = figure.add_subplot(111, projection="3d")
    colors = plt.get_cmap("tab20")
    gap = max(2.0, *(truck.dimensions.width * 0.35 for truck in run.problem.trucks))
    offset = 0.0
    max_length = max(truck.dimensions.length for truck in run.problem.trucks)
    max_height = max(truck.dimensions.height for truck in run.problem.trucks)

    for truck in run.problem.trucks:
        dimensions = truck.dimensions
        outline = Poly3DCollection(
            _box_faces(offset, 0, 0, dimensions.width, dimensions.length, dimensions.height),
            facecolors=(1, 1, 1, 0), edgecolors="#7d899b", linewidths=1.2,
        )
        axis.add_collection3d(outline)
        axis.text(
            offset + dimensions.width / 2,
            dimensions.length / 2,
            dimensions.height + 0.45,
            truck.id,
            ha="center",
            fontsize=9,
            weight="bold",
        )
        placements = (
            placement for placement in run.result.best_state.placements
            if placement.truck_id == truck.id and placement.position is not None
        )
        for index, placement in enumerate(placements):
            package = run.problem.package(placement.package_id)
            size = package.dimensions.oriented(placement.orientation)
            position = placement.position
            assert position is not None
            x = offset + position.x
            collection = Poly3DCollection(
                _box_faces(x, position.y, position.z, size.width, size.length, size.height),
                facecolors=colors(index % 20), edgecolors="#263244", linewidths=0.65,
                alpha=1.0,
            )
            axis.add_collection3d(collection)
            axis.text(
                x + size.width / 2,
                position.y + size.length / 2,
                position.z + size.height + max(0.12, max_height * 0.025),
                package.id,
                ha="center",
                va="bottom",
                fontsize=8,
                weight="bold",
                color="#172033",
                zorder=1000,
                bbox={
                    "boxstyle": "round,pad=0.25",
                    "facecolor": (1, 1, 1, 0.88),
                    "edgecolor": (1, 1, 1, 0.95),
                    "linewidth": 0.5,
                },
            )
        offset += dimensions.width + gap

    axis.set_xlim(0, max(1.0, offset - gap))
    axis.set_ylim(0, max_length)
    axis.set_zlim(0, max_height + 1)
    axis.view_init(elev=24, azim=-56)
    axis.set_box_aspect((max(1.0, offset - gap), max_length, max_height + 1))
    axis.set_axis_off()
    figure.savefig(path, dpi=170, facecolor="#f8fafc")
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
        prefix = run.run_id
        result_data = run.to_dict()
        result_data["problem"] = problem_to_data(run.problem)
        _write_json(temporary_dir / f"{prefix}-hasil.json", result_data)
        _write_trajectory(temporary_dir / f"{prefix}-trajectory.csv", run)
        _write_objective_plot(temporary_dir / f"{prefix}-objective.png", run)
        _write_3d_viewer(temporary_dir / f"{prefix}-3d-viewer.png", run)
        temporary_dir.replace(final_dir)
    except Exception:
        if temporary_dir.exists():
            shutil.rmtree(temporary_dir)
        raise
    return final_dir


__all__ = ["TRACE_FIELDS", "write_run_artifacts"]
