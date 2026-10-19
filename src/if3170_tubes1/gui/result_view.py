from __future__ import annotations

import json

import streamlit as st

from ..domain.model import Problem, State
from ..search.run import AlgorithmKind, RunConfig, SearchResult
from .charts import render_trace
from .state_view import render_state


def render_result_area(
    problem: Problem,
    preview: State,
    config: RunConfig,
    result: SearchResult | None,
    elapsed_seconds: float | None,
) -> None:
    st.divider()
    st.subheader("Visualisasi solusi")
    if result is not None:
        columns = st.columns(3)
        columns[0].metric("Best objective", f"{result.best_objective:,.2f}")
        columns[1].metric("Evaluasi", result.evaluations_used)
        columns[2].metric("Durasi", f"{elapsed_seconds:.2f} s" if elapsed_seconds is not None else "—")
        st.caption(f"Berhenti karena: {result.stopped_reason.value}")
        st.download_button(
            "Unduh hasil JSON",
            data=json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
            file_name="search-result.json",
            mime="application/json",
        )

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
