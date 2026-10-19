from __future__ import annotations

import json
import random
from pathlib import Path

import streamlit as st
from pydantic import ValidationError

from domain import build_random_state, validate_state
from execution import execute_run
from gui.experiment_view import render_experiment_area
from gui.input_form import (
    ALGORITHM_LABELS,
    OBJECTIVE_LABELS,
    render_problem_editor,
    render_run_config,
)
from gui.result_view import render_result_area
from gui.theme import (
    apply_theme,
    render_page_header,
    render_section,
    render_setup_strip,
    render_sidebar_brand,
    render_success,
)
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
        st.markdown(f"- **{location}**: {item['msg']}")


def _render_data_source() -> None:
    with st.expander("Problem JSON"):
        uploaded = st.file_uploader("Upload JSON", type=["json"], label_visibility="collapsed")
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


def main() -> None:
    st.set_page_config(
        page_title="Cargo Lab · IF3170",
        page_icon="📦",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_theme()

    if "draft" not in st.session_state:
        st.session_state["draft"] = example_problem_data()
    if "editor_version" not in st.session_state:
        st.session_state["editor_version"] = 0

    with st.sidebar:
        render_sidebar_brand()
        mode = st.radio(
            "Mode",
            ("Single Run", "Experiments"),
            horizontal=True,
            key="workspace_mode",
        )
        _render_data_source()
        if mode == "Single Run":
            config = render_run_config()
            with st.expander("Output"):
                persist_artifacts = st.toggle(
                    "Simpan artefak run",
                    value=True,
                    help="Simpan state, metrics, trajectory, dan grafik ke output/runs.",
                )
        else:
            config = None
            persist_artifacts = False

    render_page_header(mode=mode)
    render_section("01", "Data armada")
    with st.container(border=True):
        payload = render_problem_editor(
            st.session_state["draft"], st.session_state["editor_version"]
        )
    st.session_state["draft"] = payload

    if mode == "Experiments":
        try:
            experiment_problem = parse_problem_data(payload)
        except ValidationError as error:
            _show_validation_error(error)
            return
        render_experiment_area(experiment_problem)
        return

    assert config is not None
    problem_token = json.dumps(payload, sort_keys=True, ensure_ascii=False)
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
        export_data = json.dumps(
            problem_to_data(export_problem), ensure_ascii=False, indent=2
        )

    action_left, action_right, action_space = st.columns([1.35, 1, 1.8])
    with action_left:
        validate_clicked = st.button(
            "Validasi test case & buat preview",
            type="primary",
            width="stretch",
            help="Validasi input dan bangun initial state tanpa menjalankan pencarian.",
        )
    with action_right:
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
                st.error("Preview tidak memenuhi constraint domain.")
                _clear_preview()
            else:
                st.session_state["validated_problem"] = problem
                st.session_state["preview"] = preview
                st.session_state["preview_token"] = preview_token
                render_success("Data valid. Preview siap.")

    problem = st.session_state.get("validated_problem")
    preview = st.session_state.get("preview")
    available = config.algorithm in RUNNERS

    render_section("02", "Jalankan pencarian")
    render_setup_strip(
        algorithm=ALGORITHM_LABELS[config.algorithm],
        objective=OBJECTIVE_LABELS[config.objective],
        seed=config.seed,
        budget=config.max_evaluations,
    )

    run_col, run_space = st.columns([1.35, 2.85])
    with run_col:
        run_clicked = st.button(
            "Mulai pencarian",
            type="primary",
            width="stretch",
            disabled=problem is None or not available,
        )

    if run_clicked:
        progress = st.progress(0, text="Menyiapkan pencarian…")
        status = st.empty()

        def on_progress(point) -> None:
            fraction = min(1.0, point.evaluations / config.max_evaluations)
            progress.progress(
                fraction,
                text=f"{point.evaluations:,} / {config.max_evaluations:,} evaluasi",
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
            render_success(
                f"Run selesai dalam {completed.elapsed_seconds:.3f} detik."
            )

    if problem is not None and preview is not None:
        render_result_area(
            problem,
            preview,
            config,
            st.session_state.get("completed_run"),
        )


if __name__ == "__main__":
    main()
