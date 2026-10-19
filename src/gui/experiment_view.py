from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st
from pydantic import ValidationError

from domain.model import ObjectiveKind, Problem
from experiments import ExperimentConfig, PROTOCOLS, build_run_specs, run_experiment
from problem_io.problem_json import parse_problem_json, problem_to_data

from .theme import render_section, render_success


_PROTOCOL_LABELS = {
    "specification": "Spesifikasi non-GA · 15 run",
    "non_ga": "Non-GA · 15 run",
    "ga_population_sweep": "GA · sweep population · 9 run",
    "ga_generation_sweep": "GA · sweep generations · 9 run",
    "fairness": "Fairness · Steepest, SA, GA · 9 run",
    "hc_comparison": "Perbandingan HC · 12 run",
}

_FIXTURE_FILES = {
    "Data dari editor": None,
    "Tiny exact": "tiny_exact.json",
    "Single-truck constrained": "single_truck_constrained.json",
    "Multi-truck constrained": "multi_truck_constrained.json",
}
_VISIBLE_PROTOCOLS = tuple(protocol for protocol in PROTOCOLS if protocol != "non_ga")


def _selected_problem(editor_problem: Problem, fixture_label: str) -> Problem:
    fixture_name = _FIXTURE_FILES[fixture_label]
    if fixture_name is None:
        return editor_problem
    fixture_path = Path(__file__).resolve().parents[2] / "tests" / fixture_name
    return parse_problem_json(fixture_path.read_bytes())


def _run_matrix(config: ExperimentConfig) -> pd.DataFrame:
    rows = []
    for spec in build_run_specs(config):
        run_config = spec.config
        rows.append(
            {
                "Case": spec.case_id,
                "Algoritma": run_config.algorithm.value,
                "Seed": run_config.seed,
                "Konfigurasi": spec.group_label,
                "Budget": run_config.max_evaluations,
                "Parameter": json.dumps(
                    {
                        "population_size": run_config.population_size,
                        "generations": run_config.generations,
                        "max_sideways": run_config.max_sideways,
                        "max_iterations": run_config.max_iterations,
                        "num_restarts": run_config.num_restarts,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            }
        )
    return pd.DataFrame(rows)


def _filtered_runs(runs: pd.DataFrame) -> pd.DataFrame:
    algorithms = sorted(runs["algorithm"].dropna().unique().tolist())
    seeds = sorted(runs["seed"].dropna().unique().tolist())
    groups = sorted(runs["group_label"].dropna().unique().tolist())
    columns = st.columns(3)
    with columns[0]:
        selected_algorithms = st.multiselect(
            "Algoritma", algorithms, default=algorithms, key="experiment_algorithm_filter"
        )
    with columns[1]:
        selected_seeds = st.multiselect(
            "Seed", seeds, default=seeds, key="experiment_seed_filter"
        )
    with columns[2]:
        selected_groups = st.multiselect(
            "Konfigurasi", groups, default=groups, key="experiment_group_filter"
        )
    return runs[
        runs["algorithm"].isin(selected_algorithms)
        & runs["seed"].isin(selected_seeds)
        & runs["group_label"].isin(selected_groups)
    ]


def _render_comparison_chart(runs: pd.DataFrame) -> None:
    successful = runs[runs["status"] == "success"]
    if successful.empty:
        st.info("Belum ada run berhasil untuk divisualisasikan.")
        return

    chart_summary = successful.groupby("group_label", as_index=False).agg(
        best_objective=("best_objective", "median"),
        elapsed_seconds=("elapsed_seconds", "median"),
        evaluations=("evaluations", "median"),
    )
    metric_labels = {
        "best_objective": "Median best objective",
        "elapsed_seconds": "Median durasi (detik)",
        "evaluations": "Median evaluasi",
    }
    metric = st.selectbox(
        "Metrik perbandingan",
        list(metric_labels),
        format_func=metric_labels.get,
        key="experiment_chart_metric",
    )
    figure = px.bar(
        chart_summary,
        x="group_label",
        y=metric,
        color="group_label",
        labels={"group_label": "Konfigurasi", metric: metric_labels[metric]},
        text_auto=".3g",
        color_discrete_sequence=["#315CF4", "#12A594", "#F97316", "#8B5CF6"],
    )
    figure.update_layout(
        height=420,
        showlegend=False,
        margin={"l": 16, "r": 16, "t": 20, "b": 60},
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font={"family": "Aptos, Segoe UI Variable Text, Inter, sans-serif"},
        xaxis_title=None,
        yaxis_title=metric_labels[metric],
        yaxis_gridcolor="#E5E9F0",
    )
    st.plotly_chart(figure, width="stretch", config={"displaylogo": False})


def _render_results(result: dict[str, Any]) -> None:
    render_section("03", "Hasil eksperimen")
    counts = st.columns(3)
    counts[0].metric("Berhasil", result["successful_runs"])
    counts[1].metric("Gagal", result["failed_runs"])
    counts[2].metric("Total run", result["expected_runs"])

    runs = pd.DataFrame(result["runs"])
    summary = pd.DataFrame(result["summary"])
    if runs.empty:
        st.info("Belum ada hasil run.")
        return

    overview_tab, runs_tab, export_tab = st.tabs(["Perbandingan", "Detail run", "Ekspor"])
    with overview_tab:
        _render_comparison_chart(runs)
        with st.expander("Ringkasan agregat"):
            st.dataframe(summary, hide_index=True, width="stretch")

    with runs_tab:
        filtered = _filtered_runs(runs)
        visible_columns = [
            column
            for column in (
                "status",
                "algorithm",
                "seed",
                "group_label",
                "best_objective",
                "best_total_value",
                "evaluations",
                "iterations",
                "elapsed_seconds",
                "stopped_reason",
                "error",
            )
            if column in filtered.columns
        ]
        st.dataframe(filtered[visible_columns], hide_index=True, width="stretch")

    with export_tab:
        download_runs, download_summary = st.columns(2)
        with download_runs:
            st.download_button(
                "Unduh runs.csv",
                data=runs.to_csv(index=False).encode("utf-8"),
                file_name=f"{result['experiment_id']}-runs.csv",
                mime="text/csv",
                width="stretch",
            )
        with download_summary:
            st.download_button(
                "Unduh summary.csv",
                data=summary.to_csv(index=False).encode("utf-8"),
                file_name=f"{result['experiment_id']}-summary.csv",
                mime="text/csv",
                width="stretch",
            )
        st.code(str(result["experiment_dir"]), language=None)


def render_experiment_area(editor_problem: Problem) -> None:
    render_section("02", "Konfigurasi eksperimen")
    with st.container(border=True):
        first_row = st.columns([1.25, 1.25])
        with first_row[0]:
            fixture_label = st.selectbox("Dataset", list(_FIXTURE_FILES))
        with first_row[1]:
            protocol = st.selectbox(
                "Protokol",
                _VISIBLE_PROTOCOLS,
                format_func=lambda value: _PROTOCOL_LABELS.get(value, value),
            )

        try:
            problem = _selected_problem(editor_problem, fixture_label)
        except (OSError, ValueError, ValidationError) as error:
            st.error(f"Dataset tidak dapat dimuat: {error}")
            return

        second_row = st.columns([1, 1, 1])
        with second_row[0]:
            objective = ObjectiveKind(
                st.selectbox(
                    "Objective",
                    list(ObjectiveKind),
                    format_func=lambda value: (
                        "Total value"
                        if value is ObjectiveKind.TOTAL_VALUE
                        else "Urgency-adjusted value"
                    ),
                )
            )
        with second_row[1]:
            seed_text = st.text_input(
                "Seeds", value="42, 137, 2026", help="Pisahkan dengan koma."
            )
        with second_row[2]:
            max_evaluations = st.number_input(
                "Budget per run",
                min_value=1,
                max_value=1_000_000,
                value=50_000,
                step=1_000,
                disabled=protocol == "fairness",
                help="Fairness menggunakan budget tetap 50.000.",
            )

    try:
        seeds = tuple(int(value.strip()) for value in seed_text.split(",") if value.strip())
        config = ExperimentConfig(
            protocol=protocol,
            problem=problem,
            objective=objective,
            seeds=seeds,
            max_evaluations=int(max_evaluations),
        )
        matrix = _run_matrix(config)
    except (ValueError, TypeError) as error:
        st.error(f"Konfigurasi eksperimen tidak valid: {error}")
        return

    summary_columns = st.columns(3)
    summary_columns[0].metric("Run", len(matrix))
    summary_columns[1].metric("Truk", len(problem.trucks))
    summary_columns[2].metric("Paket", len(problem.packages))
    with st.expander("Lihat matriks run"):
        st.dataframe(matrix, hide_index=True, width="stretch")

    config_token = json.dumps(
        {
            "problem": problem_to_data(problem),
            "protocol": protocol,
            "objective": objective.value,
            "seeds": seeds,
            "max_evaluations": int(max_evaluations),
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    if st.session_state.get("experiment_config_token") != config_token:
        st.session_state.pop("experiment_result", None)
        st.session_state["experiment_config_token"] = config_token

    run_col, run_space = st.columns([1.2, 2.8])
    with run_col:
        run_clicked = st.button(
            "Mulai eksperimen",
            type="primary",
            width="stretch",
            key="start_experiment",
        )

    if run_clicked:
        progress = st.progress(0, text=f"Menyiapkan {len(matrix)} run…")
        status = st.empty()

        def update_progress(done: int, total: int, spec, record) -> None:
            progress.progress(done / total, text=f"Run {done} dari {total}")
            state = "berhasil" if record["status"] == "success" else "gagal"
            status.caption(f"{spec.config.algorithm.value} · seed {spec.config.seed}: {state}")

        try:
            result = run_experiment(config, on_progress=update_progress)
        except Exception as error:
            st.error(f"Eksperimen berhenti: {error}")
        else:
            st.session_state["experiment_result"] = result
            if result["failed_runs"]:
                st.warning(f"Selesai dengan {result['failed_runs']} run gagal.")
            else:
                render_success("Semua run eksperimen selesai.")

    result = st.session_state.get("experiment_result")
    if result is not None:
        _render_results(result)


__all__ = ["render_experiment_area"]
