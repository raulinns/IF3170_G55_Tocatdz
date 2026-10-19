from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from ..domain.model import Problem, State
from ..execution.model import CompletedRun
from ..search.run import AlgorithmKind, RunConfig, SearchResult
from .charts import render_trace
from .state_view import render_state


def _metric_value(value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:,.3f}"
    return str(value)


def _render_algorithm_metrics(result: SearchResult, metrics: dict[str, object]) -> None:
    algorithm_metrics = metrics["algorithm_metrics"]
    assert isinstance(algorithm_metrics, dict)
    st.markdown("#### Detail algoritma")

    if result.algorithm is AlgorithmKind.RANDOM_RESTART:
        columns = st.columns(3)
        columns[0].metric("Climb dijalankan", algorithm_metrics["attempts"])
        columns[1].metric("Restart", algorithm_metrics["restarts_completed"])
        columns[2].metric(
            "Restart terbaik",
            _metric_value(algorithm_metrics["best_restart"]),
        )
        details = algorithm_metrics.get("per_restart", [])
        if details:
            st.dataframe(pd.DataFrame(details), hide_index=True, width="stretch")
        return

    display_fields = {
        AlgorithmKind.STEEPEST_ASCENT: (
            ("Improving moves", "improving_moves"),
        ),
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
            ("Generasi selesai", "generations_completed"),
            ("Mean populasi akhir", "final_population_mean"),
            ("Generasi terbaik", "best_generation"),
        ),
    }
    fields = display_fields[result.algorithm]
    columns = st.columns(len(fields))
    for column, (label, key) in zip(columns, fields):
        column.metric(label, _metric_value(algorithm_metrics.get(key)))


def render_result_area(
    problem: Problem,
    preview: State,
    config: RunConfig,
    completed: CompletedRun | None,
) -> None:
    st.divider()
    st.markdown('<div class="section-kicker">Solution explorer</div>', unsafe_allow_html=True)
    st.subheader("Visualisasi solusi")
    result = None if completed is None else completed.result
    if completed is not None:
        metrics = completed.metrics
        columns = st.columns(7)
        columns[0].metric("Best objective", f"{result.best_objective:,.2f}")
        columns[1].metric("Raw value", f"{metrics['best_total_value']:,.2f}")
        columns[2].metric("Urgency score", f"{metrics['best_urgency_score']:,.2f}")
        columns[3].metric("Iterasi", metrics["iterations"])
        columns[4].metric("Evaluasi", result.evaluations_used)
        columns[5].metric("Paket masuk", metrics["inside_count"])
        columns[6].metric("Durasi", f"{completed.elapsed_seconds:.3f} s")

        st.markdown(
            f"**{metrics['algorithm_name']}** · objective `{result.objective.value}` · "
            f"berhenti karena `{result.stopped_reason.value}`"
        )
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
            st.caption(f"Artefak lokal: `{completed.artifact_dir}`")
        _render_algorithm_metrics(result, metrics)

    initial_tab, final_tab, best_tab, chart_tab = st.tabs(
        ["Initial state", "Final state", "Best state", "Grafik"]
    )
    with initial_tab:
        if result is None:
            st.caption("Preview acak berdasarkan seed. Setelah run, tab ini menampilkan initial state dari algoritma.")
            render_state(problem, preview, config.objective, key="preview")
        else:
            if result.algorithm is AlgorithmKind.GENETIC_ALGORITHM:
                st.caption("Individu terbaik dari populasi awal GA.")
            render_state(problem, result.initial_state, result.objective, key="initial")
    with final_tab:
        if result is None:
            st.info("Final state akan tampil setelah runner algoritma terintegrasi dan dijalankan.")
        else:
            render_state(problem, result.final_state, result.objective, key="final")
    with best_tab:
        if result is None:
            st.info("Best state akan tampil setelah runner algoritma terintegrasi dan dijalankan.")
        else:
            render_state(problem, result.best_state, result.objective, key="best")
    with chart_tab:
        if result is None:
            st.info("Grafik objective akan tampil dari TracePoint hasil run yang nyata.")
        else:
            render_trace(result)


__all__ = ["render_result_area"]
