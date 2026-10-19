from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..search.run import AlgorithmKind, SearchResult


def make_objective_figure(
    result: SearchResult,
    *,
    use_evaluations: bool = False,
) -> go.Figure:
    points = result.trace
    x_values = (
        [point.evaluations for point in points]
        if use_evaluations
        else [
            point.generation if point.generation is not None else point.step
            for point in points
        ]
    )
    is_ga = result.algorithm is AlgorithmKind.GENETIC_ALGORITHM
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x_values,
            y=[point.objective for point in points],
            mode="lines+markers",
            name="Maksimum populasi" if is_ga else "Objective saat ini",
            line={"color": "#2563EB", "width": 3},
            marker={"size": 6},
        )
    )
    mean_values = [getattr(point, "population_mean_objective", None) for point in points]
    if is_ga and any(value is not None for value in mean_values):
        fig.add_trace(
            go.Scatter(
                x=x_values,
                y=mean_values,
                mode="lines+markers",
                name="Rata-rata populasi",
                line={"color": "#EA580C", "width": 3, "dash": "dash"},
                marker={"size": 5},
            )
        )
    else:
        fig.add_trace(
            go.Scatter(
                x=x_values,
                y=[point.best_objective for point in points],
                mode="lines",
                name="Terbaik sejauh ini",
                line={"color": "#0D9488", "width": 2, "dash": "dash"},
            )
        )

    fig.update_layout(
        xaxis_title=(
            "Objective evaluations"
            if use_evaluations
            else ("Generasi" if is_ga else "Iterasi")
        ),
        yaxis_title="Nilai objective",
        hovermode="x unified",
        legend={"orientation": "h", "y": 1.16, "x": 0},
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
        height=380,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font={"color": "#15243B"},
        xaxis={"showgrid": True, "gridcolor": "#E5EBF3"},
        yaxis={"showgrid": True, "gridcolor": "#E5EBF3"},
    )
    return fig


def render_trace(result: SearchResult) -> None:
    if not result.trace:
        st.info("Algoritma ini belum menghasilkan titik grafik.")
        return
    axis_mode = st.radio(
        "Sumbu trajectory",
        ("Iterasi", "Evaluasi"),
        horizontal=True,
        key="trajectory_axis",
    )
    st.plotly_chart(
        make_objective_figure(result, use_evaluations=axis_mode == "Evaluasi"),
        width="stretch",
        key="objective_trace",
        config={"displaylogo": False},
    )
    if any(point.accept_prob is not None for point in result.trace):
        probability_label = (
            "Probabilitas pemilihan uphill move"
            if result.algorithm is AlgorithmKind.STOCHASTIC
            else "Peluang penerimaan"
        )
        fig = go.Figure(
            go.Scatter(
                x=[point.step for point in result.trace],
                y=[point.accept_prob for point in result.trace],
                mode="lines+markers",
                name=probability_label,
                line={"color": "#EA580C", "width": 2},
            )
        )
        fig.update_layout(
            xaxis_title="Iterasi",
            yaxis_title=probability_label,
            yaxis_range=[0, 1],
            height=300,
            margin={"l": 20, "r": 20, "t": 20, "b": 20},
        )
        st.plotly_chart(fig, width="stretch", key="move_probability")

    if result.algorithm is AlgorithmKind.SIMULATED_ANNEALING and any(
        point.temperature is not None for point in result.trace
    ):
        temperature = go.Figure(
            go.Scatter(
                x=[point.step for point in result.trace],
                y=[point.temperature for point in result.trace],
                mode="lines+markers",
                name="Temperatur",
                line={"color": "#7C3AED", "width": 3},
            )
        )
        stuck_points = [point for point in result.trace if point.stuck is True]
        if stuck_points:
            temperature.add_trace(
                go.Scatter(
                    x=[point.step for point in stuck_points],
                    y=[point.temperature for point in stuck_points],
                    mode="markers",
                    name="Episode stuck",
                    marker={"color": "#DC2626", "size": 10, "symbol": "x"},
                )
            )
        temperature.update_layout(
            xaxis_title="Iterasi",
            yaxis_title="Temperatur",
            yaxis_type="log",
            height=320,
            margin={"l": 20, "r": 20, "t": 20, "b": 20},
        )
        st.plotly_chart(temperature, width="stretch", key="sa_temperature")
    st.caption("Data grafik juga tersedia sebagai tabel untuk membaca nilai secara tepat.")
    st.dataframe(
        pd.DataFrame(result.trace_rows()),
        hide_index=True,
        width="stretch",
    )


__all__ = ["make_objective_figure", "render_trace"]
