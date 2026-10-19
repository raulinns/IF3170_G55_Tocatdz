from __future__ import annotations

import hashlib
import json

import pandas as pd
import streamlit as st

from analysis.reference import knapsack_upper_bound, solve_tiny_exact
from domain.constraints import validate_state
from domain.model import Problem, State
from execution.model import CompletedRun
from problem_io.problem_json import problem_to_data
from search.run import AlgorithmKind, RunConfig, SearchResult, state_to_dict

from .charts import render_trace
from .state_view import render_state
from .theme import render_section


def _metric_value(value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:,.3f}"
    return str(value)


def _render_algorithm_metrics(result: SearchResult, metrics: dict[str, object]) -> None:
    algorithm_metrics = metrics["algorithm_metrics"]
    assert isinstance(algorithm_metrics, dict)

    if result.algorithm is AlgorithmKind.RANDOM_RESTART:
        columns = st.columns(3)
        columns[0].metric("Climb", algorithm_metrics["attempts"])
        columns[1].metric("Restart", algorithm_metrics["restarts_completed"])
        columns[2].metric("Restart terbaik", _metric_value(algorithm_metrics["best_restart"]))
        details = algorithm_metrics.get("per_restart", [])
        if details:
            st.dataframe(pd.DataFrame(details), hide_index=True, width="stretch")
        return

    display_fields = {
        AlgorithmKind.STEEPEST_ASCENT: (("Improving moves", "improving_moves"),),
        AlgorithmKind.SIDEWAYS: (
            ("Sideways moves", "sideways_moves"),
            ("Maks. berturut-turut", "max_consecutive_sideways"),
        ),
        AlgorithmKind.STOCHASTIC: (
            ("Uphill terpilih", "uphill_moves_selected"),
            ("Rerata probabilitas", "mean_selection_probability"),
        ),
        AlgorithmKind.SIMULATED_ANNEALING: (
            ("Move diterima", "accepted_moves"),
            ("Move ditolak", "rejected_moves"),
            ("Downhill diterima", "downhill_moves_accepted"),
            ("Episode stuck", "stuck_episodes"),
            ("Temperatur akhir", "final_temperature"),
        ),
        AlgorithmKind.GENETIC_ALGORITHM: (
            ("Generasi", "generations_completed"),
            ("Mean populasi akhir", "final_population_mean"),
            ("Generasi terbaik", "best_generation"),
        ),
    }
    fields = display_fields[result.algorithm]
    columns = st.columns(len(fields))
    for column, (label, field_key) in zip(columns, fields):
        column.metric(label, _metric_value(algorithm_metrics.get(field_key)))


def _render_reference(problem: Problem, config: RunConfig, result: SearchResult | None) -> None:
    problem_key = json.dumps(problem_to_data(problem), sort_keys=True)
    digest = hashlib.sha256(problem_key.encode("utf-8")).hexdigest()[:12]
    state_key = f"reference:{digest}:{config.objective.value}"

    if len(problem.packages) <= 6:
        if st.button(
            "Hitung exact optimum",
            key=f"exact:{state_key}",
            help="Telusuri ruang solusi kecil untuk memperoleh pembanding global.",
        ):
            reference = solve_tiny_exact(problem, config.objective)
            st.session_state[state_key] = {
                "kind": "exact",
                "value": reference.value,
                "state": state_to_dict(reference.state),
                "nodes": reference.nodes_explored,
                "feasible": validate_state(problem, reference.state).is_valid,
            }
    else:
        if st.button(
            "Hitung knapsack upper bound",
            key=f"bound:{state_key}",
            help="Hitung batas atas yang mengabaikan constraint geometri.",
        ):
            st.session_state[state_key] = {
                "kind": "upper_bound",
                "value": knapsack_upper_bound(problem, config.objective),
            }

    reference = st.session_state.get(state_key)
    if reference is None:
        return

    if reference["kind"] == "exact":
        columns = st.columns(3)
        columns[0].metric("Exact optimum", _metric_value(reference["value"]))
        columns[1].metric("Node", reference["nodes"])
        columns[2].metric("Feasible", "Ya" if reference["feasible"] else "Tidak")
        if result is not None and result.objective == config.objective:
            gap = max(0.0, reference["value"] - result.best_objective)
            st.metric("Gap ke optimum", _metric_value(gap))
        st.download_button(
            "Unduh exact certificate",
            data=json.dumps(
                {
                    "objective": config.objective.value,
                    "value": reference["value"],
                    "feasible": reference["feasible"],
                    "state": reference["state"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            file_name="exact-reference-certificate.json",
            mime="application/json",
            key=f"certificate:{state_key}",
        )
    else:
        st.metric("Knapsack upper bound", _metric_value(reference["value"]))
        if result is not None and result.objective == config.objective:
            gap = max(0.0, reference["value"] - result.best_objective)
            st.metric("Gap ke upper bound", _metric_value(gap))


def _render_run_details(completed: CompletedRun) -> None:
    result = completed.result
    metrics = completed.metrics
    detail_columns = st.columns(3)
    detail_columns[0].metric("Iterasi", metrics["iterations"])
    detail_columns[1].metric("Evaluasi", result.evaluations_used)
    detail_columns[2].metric("Stop reason", result.stopped_reason.value.replace("_", " ").title())
    _render_algorithm_metrics(result, metrics)

    download_result, download_metrics = st.columns(2)
    with download_result:
        st.download_button(
            "Unduh search result",
            data=json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
            file_name=f"{completed.run_id}-result.json",
            mime="application/json",
            width="stretch",
        )
    with download_metrics:
        st.download_button(
            "Unduh metrics",
            data=json.dumps(metrics, ensure_ascii=False, indent=2),
            file_name=f"{completed.run_id}-metrics.json",
            mime="application/json",
            width="stretch",
        )
    if completed.artifact_dir is not None:
        st.code(str(completed.artifact_dir), language=None)


def render_result_area(
    problem: Problem,
    preview: State,
    config: RunConfig,
    completed: CompletedRun | None,
) -> None:
    render_section("03", "Eksplorasi solusi")
    result = None if completed is None else completed.result

    if completed is None:
        st.markdown("#### Initial state")
        render_state(problem, preview, config.objective, key="preview")
    else:
        metrics = completed.metrics
        columns = st.columns(4)
        columns[0].metric("Best objective", f"{result.best_objective:,.2f}")
        columns[1].metric("Total value", f"{metrics['best_total_value']:,.2f}")
        columns[2].metric("Paket masuk", metrics["inside_count"])
        columns[3].metric("Durasi", f"{completed.elapsed_seconds:.3f} s")

        best_tab, initial_tab, final_tab, chart_tab = st.tabs(
            ["Best state", "Initial state", "Final state", "Trajectory"]
        )
        with best_tab:
            render_state(problem, result.best_state, result.objective, key="best")
        with initial_tab:
            render_state(problem, result.initial_state, result.objective, key="initial")
        with final_tab:
            render_state(problem, result.final_state, result.objective, key="final")
        with chart_tab:
            render_trace(result)

        with st.expander("Detail run & unduhan"):
            _render_run_details(completed)

    with st.expander("Pembanding solusi · opsional"):
        _render_reference(problem, config, result)


__all__ = ["render_result_area"]
