from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from analysis.reference import knapsack_upper_bound, solve_tiny_exact
from domain.constraints import validate_state
from domain.objectives import summarize_state
from domain.packing import build_random_state
from execution.runner import execute_run
from experiments import ExperimentConfig, PROTOCOLS, build_run_specs, run_experiment
from problem_io.problem_json import example_problem_data, parse_problem_data, problem_to_data
from search.run import state_to_dict

from .jobs import JOBS, ProgressUpdater
from .schemas import ExperimentRequest, PreviewRequest, ReferenceRequest, RunRequest


ROOT = Path(__file__).resolve().parents[2]
RUN_OUTPUT = ROOT / "output" / "runs"
EXPERIMENT_OUTPUT = ROOT / "output" / "experiments"
FRONTEND_DIST = ROOT / "frontend" / "dist"

app = FastAPI(title="CargoLab API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _problem_or_422(data: dict[str, Any]):
    try:
        return parse_problem_data(data)
    except ValidationError as error:
        raise HTTPException(
            status_code=422,
            detail=error.errors(include_context=False),
        ) from error


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/problems/example")
def example_problem() -> dict[str, Any]:
    return example_problem_data()


@app.get("/api/problems/fixtures/{name}")
def fixture_problem(name: str) -> dict[str, Any]:
    fixtures = {
        "tiny": "tiny_exact.json",
        "single": "single_truck_constrained.json",
        "multi": "multi_truck_constrained.json",
    }
    filename = fixtures.get(name)
    if filename is None:
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan.")
    path = ROOT / "tests" / filename
    problem = _problem_or_422(json.loads(path.read_text(encoding="utf-8")))
    return problem_to_data(problem)


@app.post("/api/problems/validate")
def validate_problem(request: PreviewRequest) -> dict[str, Any]:
    problem = _problem_or_422(request.problem)
    state = build_random_state(problem, random.Random(request.seed))
    validation = validate_state(problem, state)
    if not validation.is_valid:
        raise HTTPException(
            status_code=500,
            detail="Initial state yang dibangun tidak memenuhi constraint.",
        )
    return {
        "problem": problem_to_data(problem),
        "state": state_to_dict(state),
        "summary": summarize_state(problem, state, request.objective),
    }


@app.post("/api/runs", status_code=202)
def create_run(request: RunRequest) -> dict[str, str]:
    problem = _problem_or_422(request.problem)
    config = request.config.to_domain()

    def worker(update: ProgressUpdater) -> dict[str, Any]:
        def on_progress(point) -> None:
            fraction = point.evaluations / config.max_evaluations
            update(
                fraction,
                f"{point.evaluations:,} dari {config.max_evaluations:,} evaluasi",
            )

        completed = execute_run(
            problem,
            config,
            on_progress=on_progress,
            artifact_root=RUN_OUTPUT if request.persist_artifacts else None,
        )
        result = completed.to_dict()
        result["problem"] = problem_to_data(problem)
        return jsonable_encoder(result)

    return {"job_id": JOBS.submit("run", worker)}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan.")
    return job


@app.post("/api/references")
def create_reference(request: ReferenceRequest) -> dict[str, Any]:
    problem = _problem_or_422(request.problem)
    if len(problem.packages) <= 6:
        exact = solve_tiny_exact(problem, request.objective)
        response: dict[str, Any] = {
            "kind": "exact",
            "value": exact.value,
            "nodes_explored": exact.nodes_explored,
            "state": state_to_dict(exact.state),
            "feasible": validate_state(problem, exact.state).is_valid,
        }
    else:
        response = {
            "kind": "upper_bound",
            "value": knapsack_upper_bound(problem, request.objective),
        }
    if request.candidate_value is not None:
        response["gap"] = max(0.0, response["value"] - request.candidate_value)
    return response


@app.get("/api/experiments/protocols")
def experiment_protocols() -> dict[str, list[str]]:
    return {"protocols": list(PROTOCOLS)}


@app.post("/api/experiments/preview")
def preview_experiment(request: ExperimentRequest) -> dict[str, Any]:
    problem = _problem_or_422(request.problem)
    config = ExperimentConfig(
        protocol=request.protocol,
        problem=problem,
        objective=request.objective,
        seeds=tuple(request.seeds),
        max_evaluations=request.max_evaluations,
        population_size=request.population_size,
        generations=request.generations,
    )
    specs = build_run_specs(config)
    return {
        "run_count": len(specs),
        "runs": [
            {
                "case_id": spec.case_id,
                "group": spec.group_label,
                "algorithm": spec.config.algorithm.value,
                "seed": spec.config.seed,
                "budget": spec.config.max_evaluations,
            }
            for spec in specs
        ],
    }


@app.post("/api/experiments", status_code=202)
def create_experiment(request: ExperimentRequest) -> dict[str, str]:
    problem = _problem_or_422(request.problem)
    config = ExperimentConfig(
        protocol=request.protocol,
        problem=problem,
        output_root=EXPERIMENT_OUTPUT,
        objective=request.objective,
        seeds=tuple(request.seeds),
        max_evaluations=request.max_evaluations,
        population_size=request.population_size,
        generations=request.generations,
    )

    def worker(update: ProgressUpdater) -> dict[str, Any]:
        def on_progress(done, total, spec, record) -> None:
            status = "berhasil" if record["status"] == "success" else "gagal"
            update(done / total, f"{spec.config.algorithm.value} · seed {spec.config.seed}: {status}")

        return jsonable_encoder(run_experiment(config, on_progress=on_progress))

    return {"job_id": JOBS.submit("experiment", worker)}


if FRONTEND_DIST.exists():
    assets = FRONTEND_DIST / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        requested = (FRONTEND_DIST / path).resolve()
        if path and requested.is_relative_to(FRONTEND_DIST.resolve()) and requested.is_file():
            return FileResponse(requested)
        return FileResponse(FRONTEND_DIST / "index.html")


__all__ = ["app"]
