from __future__ import annotations

import json
import random
from pathlib import Path

import streamlit as st
from pydantic import ValidationError

from domain import build_random_state, validate_state
from execution import execute_run
from gui.input_form import (
    ALGORITHM_LABELS,
    render_problem_editor,
    render_run_config,
)
from gui.experiment_view import render_experiment_area
from gui.result_view import render_result_area
from problem_io import (
    example_problem_data,
    parse_problem_data,
    parse_problem_draft_json,
    problem_to_data,
)
from search.dispatch import RUNNERS


def _clear_preview() -> None:
    for key in (
        "validated_problem",
        "preview",
        "preview_token",
        "completed_run",
        "result_token",
    ):
        st.session_state.pop(key, None)


def _show_validation_error(error: ValidationError) -> None:
    st.error("Data belum valid. Periksa field berikut, lalu coba lagi.")
    for item in error.errors():
        location = " → ".join(str(part) for part in item["loc"]) or "problem"
        st.write(f"• **{location}**: {item['msg']}")


def main() -> None:
    st.set_page_config(page_title="Cargo Lab · IF3170", layout="wide")
    st.markdown(
        """
        <style>
        .block-container {max-width: 1320px; padding-top: 2rem; padding-bottom: 3rem;}
        .hero {background: linear-gradient(115deg, #173A75 0%, #2563EB 100%);
            color: white; padding: 2.2rem 2.5rem; border-radius: 20px;
            margin-bottom: 1.6rem; box-shadow: 0 12px 34px rgba(24,58,117,.15);}
        .hero .eyebrow {font-size: .8rem; letter-spacing: .18em; font-weight: 700; opacity: .84;}
        .hero h1 {color: white; font-size: clamp(2rem, 3.2vw, 3.2rem);
            margin: .45rem 0 .5rem; letter-spacing: -.035em;}
        .hero p {font-size: 1.05rem; color: #E8F1FF; margin: 0; max-width: 740px;}
        [data-testid="stMetric"] {background: #FFFFFF; border: 1px solid #DDE6F2;
            border-radius: 16px; padding: .9rem 1rem; box-shadow: 0 5px 20px rgba(23,58,117,.06);}
        [data-testid="stMetricValue"] {font-variant-numeric: tabular-nums;}
        [data-testid="stSidebar"] {background: #F6F8FC; border-right: 1px solid #E2E8F0;}
        [data-testid="stDataFrame"], [data-testid="stPlotlyChart"] {
            border-radius: 16px; overflow: hidden;}
        .section-kicker {color: #2563EB; font-size: .74rem; letter-spacing: .14em;
            text-transform: uppercase; font-weight: 800; margin-bottom: .2rem;}
        .run-banner {background: linear-gradient(135deg, #F8FAFF, #EEF5FF);
            border: 1px solid #D9E7FF; border-radius: 18px; padding: 1rem 1.2rem;
            margin: .4rem 0 1rem; color: #173A75;}
        h2, h3 {letter-spacing: -.02em;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="hero">
            <div class="eyebrow">IF3170 · LOCAL SEARCH WORKSPACE</div>
            <h1>Cargo Lab</h1>
            <p>Susun paket, periksa batasan armada, dan lihat solusi penempatan dalam ruang tiga dimensi.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "draft" not in st.session_state:
        st.session_state["draft"] = example_problem_data()
    if "editor_version" not in st.session_state:
        st.session_state["editor_version"] = 0

    with st.sidebar:
        st.header("Sumber data")
        uploaded = st.file_uploader("Upload problem JSON", type=["json"])
        if st.button("Muat ke editor", disabled=uploaded is None, width="stretch"):
            try:
                draft = parse_problem_draft_json(uploaded.getvalue())
            except json.JSONDecodeError as error:
                st.error(f"JSON tidak dapat dibaca pada baris {error.lineno}: {error.msg}")
            except ValidationError as error:
                _show_validation_error(error)
            else:
                st.session_state["draft"] = draft
                st.session_state["editor_version"] += 1
                _clear_preview()
                st.rerun()
        st.caption(
            "Format JSON memakai `trucks` dan `packages`. Keunikan ID diperiksa "
            "saat tombol validasi ditekan."
        )
        st.divider()
        mode = st.radio(
            "Mode kerja",
            ("Single Run", "Experiments"),
            horizontal=True,
            key="workspace_mode",
        )
        if mode == "Single Run":
            config = render_run_config()
            persist_artifacts = st.toggle(
                "Simpan artefak run",
                value=True,
                help="Menyimpan JSON, CSV, metrics, dan PNG ke output/runs.",
            )
        else:
            config = None
            persist_artifacts = False

    payload = render_problem_editor(
        st.session_state["draft"], st.session_state["editor_version"]
    )
    st.session_state["draft"] = payload
    problem_token = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    if mode == "Experiments":
        try:
            experiment_problem = parse_problem_data(payload)
        except ValidationError as error:
            _show_validation_error(error)
            return
        render_experiment_area(experiment_problem)
        st.divider()
        st.caption("Experiment workspace · setiap eksperimen disimpan terpisah di output/experiments.")
        return

    assert config is not None
    preview_token = (problem_token, config.seed)
    result_token = (preview_token, json.dumps(config.to_dict(), sort_keys=True))
    if st.session_state.get("preview_token") != preview_token:
        _clear_preview()
    elif st.session_state.get("result_token") != result_token:
        for key in ("completed_run", "result_token"):
            st.session_state.pop(key, None)

    try:
        export_problem = parse_problem_data(payload)
    except ValidationError:
        export_data = ""
    else:
        export_data = json.dumps(problem_to_data(export_problem), ensure_ascii=False, indent=2)

    st.markdown('<div class="section-kicker">Problem workspace</div>', unsafe_allow_html=True)
    summary_columns = st.columns(4)
    summary_columns[0].metric("Algoritma", ALGORITHM_LABELS[config.algorithm].split("·")[-1].strip())
    summary_columns[1].metric("Objective", config.objective.value.replace("_", " ").title())
    summary_columns[2].metric("Seed", config.seed)
    summary_columns[3].metric("Budget", f"{config.max_evaluations:,}")

    validate_col, download_col = st.columns([1.2, 1])
    with validate_col:
        validate_clicked = st.button(
            "Validasi test case & buat preview",
            type="primary",
            width="stretch",
            help=(
                "Memeriksa data dan membangun contoh initial state feasible. "
                "Langkah ini belum menjalankan algoritma pencarian."
            ),
        )
    with download_col:
        st.download_button(
            "Unduh problem JSON",
            data=export_data,
            file_name="problem.json",
            mime="application/json",
            disabled=not export_data,
            width="stretch",
        )

    if validate_clicked:
        try:
            problem = parse_problem_data(payload)
        except ValidationError as error:
            _clear_preview()
            _show_validation_error(error)
        else:
            preview = build_random_state(problem, random.Random(config.seed))
            validation = validate_state(problem, preview)
            if not validation.is_valid:
                st.error("Preview gagal memenuhi constraint domain. Periksa implementasi packing.")
                _clear_preview()
            else:
                st.session_state["validated_problem"] = problem
                st.session_state["preview"] = preview
                st.session_state["preview_token"] = preview_token
                st.success("Input valid. Preview state awal sudah siap.")

    problem = st.session_state.get("validated_problem")
    preview = st.session_state.get("preview")
    available = config.algorithm in RUNNERS
    st.divider()
    st.markdown('<div class="section-kicker">Search control</div>', unsafe_allow_html=True)
    st.subheader("Jalankan pencarian")
    st.markdown(
        f'<div class="run-banner"><b>{ALGORITHM_LABELS[config.algorithm]}</b><br>'
        f'<span>Seed {config.seed} · maksimum {config.max_evaluations:,} evaluations · '
        f'{"artefak aktif" if persist_artifacts else "tanpa artefak"}</span></div>',
        unsafe_allow_html=True,
    )
    if problem is None:
        st.caption(
            "Validasi memeriksa input dan membuat preview. Pencarian baru berjalan "
            "setelah tombol Mulai pencarian ditekan."
        )

    if st.button(
        "Mulai pencarian",
        type="primary",
        width="stretch",
        disabled=problem is None or not available,
    ):
        progress = st.progress(0, text="Menyiapkan pencarian...")
        status = st.empty()

        def on_progress(point) -> None:
            fraction = min(1.0, point.evaluations / config.max_evaluations)
            progress.progress(
                fraction,
                text=f"{point.evaluations:,} / {config.max_evaluations:,} evaluations",
            )
            status.caption(
                f"Step {point.step:,} · objective {point.objective:,.2f} · "
                f"best {point.best_objective:,.2f}"
            )

        try:
            completed = execute_run(
                problem,
                config,
                on_progress=on_progress,
                artifact_root=(Path("output") / "runs") if persist_artifacts else None,
            )
        except Exception as error:
            progress.empty()
            status.empty()
            st.error(f"Run gagal: {error}")
        else:
            progress.progress(1.0, text="Pencarian selesai")
            st.session_state["completed_run"] = completed
            st.session_state["result_token"] = result_token
            st.success(
                f"Run {completed.run_id} selesai dalam {completed.elapsed_seconds:.3f} detik."
            )

    if problem is None or preview is None:
        st.info("Isi atau upload data, lalu pilih **Validasi & buat preview** untuk melihat armada 3D.")
    else:
        render_result_area(
            problem,
            preview,
            config,
            st.session_state.get("completed_run"),
        )

    st.divider()
    st.caption("Single-run workspace · eksperimen multi-run tersedia melalui mode Experiments.")


if __name__ == "__main__":
    main()
