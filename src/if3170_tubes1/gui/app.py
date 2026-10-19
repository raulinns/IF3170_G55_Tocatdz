from __future__ import annotations

import json
import random
from time import perf_counter

import streamlit as st
from pydantic import ValidationError

from if3170_tubes1.domain import build_random_state, validate_state
from if3170_tubes1.gui.input_form import (
    ALGORITHM_LABELS,
    render_problem_editor,
    render_run_config,
)
from if3170_tubes1.gui.result_view import render_result_area
from if3170_tubes1.io import (
    example_problem_data,
    parse_problem_data,
    parse_problem_json,
    problem_to_data,
)
from if3170_tubes1.search.dispatch import RUNNERS, run_search


def _clear_preview() -> None:
    for key in ("validated_problem", "preview", "preview_token", "result", "result_token", "elapsed_seconds"):
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
            border-radius: 14px; padding: .8rem 1rem;}
        [data-testid="stMetricValue"] {font-variant-numeric: tabular-nums;}
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
        if st.button("Muat JSON", disabled=uploaded is None, width="stretch"):
            try:
                problem = parse_problem_json(uploaded.getvalue())
            except json.JSONDecodeError as error:
                st.error(f"JSON tidak dapat dibaca pada baris {error.lineno}: {error.msg}")
            except ValidationError as error:
                _show_validation_error(error)
            else:
                st.session_state["draft"] = problem_to_data(problem)
                st.session_state["editor_version"] += 1
                _clear_preview()
                st.rerun()
        st.caption("Format JSON memakai `name`, `trucks`, dan `packages`.")
        st.divider()
        config = render_run_config()

    payload = render_problem_editor(
        st.session_state["draft"], st.session_state["editor_version"]
    )
    st.session_state["draft"] = payload
    problem_token = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    preview_token = (problem_token, config.seed)
    result_token = (preview_token, json.dumps(config.to_dict(), sort_keys=True))
    if st.session_state.get("preview_token") != preview_token:
        _clear_preview()
    elif st.session_state.get("result_token") != result_token:
        for key in ("result", "result_token", "elapsed_seconds"):
            st.session_state.pop(key, None)

    try:
        export_problem = parse_problem_data(payload)
    except ValidationError:
        export_data = ""
    else:
        export_data = json.dumps(problem_to_data(export_problem), ensure_ascii=False, indent=2)

    validate_col, download_col = st.columns([1, 1])
    with validate_col:
        validate_clicked = st.button("Validasi & buat preview", type="primary", width="stretch")
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
    st.subheader("Jalankan pencarian")
    if not available:
        st.info(
            f"Runner {ALGORITHM_LABELS.get(config.algorithm, config.algorithm.value)} "
            "belum terintegrasi di branch ini. "
            "Preview tetap dapat digunakan; tombol Run akan aktif setelah runner didaftarkan."
        )
    elif problem is None:
        st.caption("Validasi input terlebih dahulu untuk mengaktifkan Run.")
    if st.button("Run algoritma", disabled=problem is None or not available):
        start = perf_counter()
        try:
            with st.spinner("Algoritma sedang berjalan..."):
                result = run_search(problem, config)
        except Exception as error:
            st.error(f"Run gagal: {error}")
        else:
            st.session_state["result"] = result
            st.session_state["elapsed_seconds"] = perf_counter() - start
            st.session_state["result_token"] = result_token
            st.success("Run selesai. Lihat final state, best state, dan grafik di bawah.")

    if problem is None or preview is None:
        st.info("Isi atau upload data, lalu pilih **Validasi & buat preview** untuk melihat armada 3D.")
    else:
        render_result_area(
            problem,
            preview,
            config,
            st.session_state.get("result"),
            st.session_state.get("elapsed_seconds"),
        )

    st.divider()
    st.caption(
        "Eksperimen multi-run akan memakai output algoritma yang nyata setelah runner dan protokol eksperimen tersedia."
    )


if __name__ == "__main__":
    main()
