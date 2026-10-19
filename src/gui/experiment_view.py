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
    fixture_path = (
        Path(__file__).resolve().parents[2]
        / "tests"
        / fixture_name
    )
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
                "Budget evaluasi": run_config.max_evaluations,
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


def _render_results(result: dict[str, Any]) -> None:
    st.subheader("Hasil eksperimen")
    counts = st.columns(3)
    counts[0].metric("Run berhasil", result["successful_runs"])
    counts[1].metric("Run gagal", result["failed_runs"])
    counts[2].metric("Total run", result["expected_runs"])
    st.caption(f"ID eksperimen: `{result['experiment_id']}` · `{result['experiment_dir']}`")
    st.caption("Ringkasan tiga seed bersifat deskriptif, bukan klaim signifikansi statistik.")

    runs = pd.DataFrame(result["runs"])
    summary = pd.DataFrame(result["summary"])
    if runs.empty:
        st.info("Belum ada hasil run untuk ditampilkan.")
        return

    st.markdown("#### Filter hasil")
    filter_columns = st.columns(3)
    algorithms = sorted(runs["algorithm"].dropna().unique().tolist())
    seeds = sorted(runs["seed"].dropna().unique().tolist())
    groups = sorted(runs["group_label"].dropna().unique().tolist())
    with filter_columns[0]:
        selected_algorithms = st.multiselect(
            "Algoritma", algorithms, default=algorithms, key="experiment_algorithm_filter"
        )
    with filter_columns[1]:
        selected_seeds = st.multiselect(
            "Seed", seeds, default=seeds, key="experiment_seed_filter"
        )
    with filter_columns[2]:
        selected_groups = st.multiselect(
            "Konfigurasi", groups, default=groups, key="experiment_group_filter"
        )

    filtered = runs[
        runs["algorithm"].isin(selected_algorithms)
        & runs["seed"].isin(selected_seeds)
        & runs["group_label"].isin(selected_groups)
    ]
    st.caption(f"Menampilkan {len(filtered)} dari {len(runs)} run; grafik mengikuti filter ini.")
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
            "sideways_moves",
            "restarts_completed",
            "generations_completed",
            "error",
            "artifact_path",
        )
        if column in filtered.columns
    ]
    st.dataframe(filtered[visible_columns], hide_index=True, width="stretch")

    st.markdown("#### Ringkasan engine (semua run eksperimen)")
    st.dataframe(summary, hide_index=True, width="stretch")
    successful_filtered = filtered[filtered["status"] == "success"]
    chart_summary = (
        successful_filtered.groupby("group_label", as_index=False)
        .agg(
            best_objective=("best_objective", "median"),
            elapsed_seconds=("elapsed_seconds", "median"),
            evaluations=("evaluations", "median"),
        )
        if not successful_filtered.empty
        else pd.DataFrame()
    )
    chart_tab, data_tab = st.tabs(["Grafik perbandingan", "Data unduhan"])
    with chart_tab:
        chart_specs = (
            ("best_objective", "Median best objective"),
            ("elapsed_seconds", "Median durasi (detik)"),
            ("evaluations", "Median jumlah evaluasi"),
        )
        chart_columns = st.columns(3)
        for column, (metric, title) in zip(chart_columns, chart_specs):
            chart_data = chart_summary
            with column:
                st.markdown(f"**{title}**")
                if chart_data.empty or chart_data[metric].isna().all():
                    st.info("Belum ada run berhasil untuk grafik ini.")
                else:
                    figure = px.bar(
                        chart_data,
                        x="group_label",
                        y=metric,
                        labels={"group_label": "Konfigurasi", metric: title},
                        text_auto=".3g",
                    )
                    figure.update_layout(
                        showlegend=False,
                        margin={"l": 8, "r": 8, "t": 8, "b": 48},
                        xaxis_title=None,
                        yaxis_title=title,
                    )
                    st.plotly_chart(figure, width="stretch")
    with data_tab:
        st.download_button(
            "Unduh runs.csv",
            data=runs.to_csv(index=False).encode("utf-8"),
            file_name=f"{result['experiment_id']}-runs.csv",
            mime="text/csv",
            width="stretch",
        )
        st.download_button(
            "Unduh summary.csv",
            data=summary.to_csv(index=False).encode("utf-8"),
            file_name=f"{result['experiment_id']}-summary.csv",
            mime="text/csv",
            width="stretch",
        )


def render_experiment_area(editor_problem: Problem) -> None:
    st.markdown('<div class="section-kicker">Experiment workspace</div>', unsafe_allow_html=True)
    st.subheader("Eksperimen multi-run")
    st.caption(
        "Pilih protokol untuk melihat matriks run, lalu jalankan. Setiap run memakai "
        "runner dan konfigurasi yang sama dengan experiment engine. Jika memilih fixture, "
        "data fixture yang dipakai, bukan data editor."
    )

    controls = st.columns([1.4, 1, 1, 1])
    with controls[0]:
        fixture_label = st.selectbox("Fixture problem", list(_FIXTURE_FILES))
    try:
        problem = _selected_problem(editor_problem, fixture_label)
    except (OSError, ValueError, ValidationError) as error:
        st.error(f"Fixture tidak dapat dimuat: {error}")
        return
    with controls[1]:
        protocol = st.selectbox(
            "Protokol",
            _VISIBLE_PROTOCOLS,
            format_func=lambda value: _PROTOCOL_LABELS.get(value, value),
        )
    with controls[2]:
        objective = ObjectiveKind(
            st.selectbox(
                "Objective",
                list(ObjectiveKind),
                format_func=lambda value: (
                    "Total value" if value is ObjectiveKind.TOTAL_VALUE else "Value per urgency"
                ),
            )
        )
    with controls[3]:
        seed_text = st.text_input("Seeds", value="42, 137, 2026", help="Pisahkan seed dengan koma.")

    budget_disabled = protocol == "fairness"
    max_evaluations = st.number_input(
        "Budget evaluasi per run non-GA",
        min_value=1,
        max_value=1_000_000,
        value=50_000,
        step=1_000,
        disabled=budget_disabled,
        help="Protocol fairness menetapkan budget 50.000 untuk semua algoritma.",
    )
    if budget_disabled:
        st.caption("Budget fairness dikunci ke 50.000 evaluasi per run.")

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

    problem_columns = st.columns(3)
    problem_columns[0].metric("Dataset", fixture_label)
    problem_columns[1].metric("Truk", len(problem.trucks))
    problem_columns[2].metric("Paket", len(problem.packages))
    st.markdown("#### Preview matriks run")
    st.metric("Estimasi jumlah run", len(matrix))
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

    run_col, note_col = st.columns([1, 3])
    with run_col:
        run_clicked = st.button(
            "Mulai eksperimen",
            type="primary",
            width="stretch",
            key="start_experiment",
        )
    with note_col:
        st.caption("Eksperimen berjalan berurutan; hasil run yang gagal tidak menghapus hasil yang berhasil.")

    if run_clicked:
        progress = st.progress(0, text=f"Menyiapkan {len(matrix)} run…")
        status = st.empty()

        def update_progress(done: int, total: int, spec, record) -> None:
            progress.progress(done / total, text=f"Run {done} dari {total}")
            state = "berhasil" if record["status"] == "success" else "gagal"
            status.caption(
                f"{spec.config.algorithm.value} · seed {spec.config.seed}: {state}"
            )

        try:
            result = run_experiment(config, on_progress=update_progress)
        except Exception as error:
            st.error(f"Eksperimen berhenti sebelum selesai: {error}")
        else:
            st.session_state["experiment_result"] = result
            if result["failed_runs"]:
                st.warning(
                    f"Selesai dengan {result['failed_runs']} run gagal. Run berhasil tetap tersedia di bawah."
                )
            else:
                st.success("Semua run eksperimen selesai.")

    result = st.session_state.get("experiment_result")
    if result is not None:
        _render_results(result)


__all__ = ["render_experiment_area"]
