from __future__ import annotations

from collections import defaultdict
from io import BytesIO

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from search.run import AlgorithmKind, SearchResult


def _x_values(result: SearchResult, use_evaluations: bool) -> list[int]:
    if use_evaluations:
        return [point.evaluations for point in result.trace]
    return [
        point.generation if point.generation is not None else point.step
        for point in result.trace
    ]


def _base_layout(fig: go.Figure, *, x_title: str, y_title: str, height: int = 360) -> go.Figure:
    fig.update_layout(
        xaxis_title=x_title,
        yaxis_title=y_title,
        hovermode="x unified",
        legend={"orientation": "h", "y": 1.16, "x": 0},
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
        height=height,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font={"color": "#15243B"},
        xaxis={"showgrid": True, "gridcolor": "#E5EBF3"},
        yaxis={"showgrid": True, "gridcolor": "#E5EBF3"},
    )
    return fig


def make_objective_figure(
    result: SearchResult,
    *,
    use_evaluations: bool = False,
) -> go.Figure:
    points = result.trace
    x_values = _x_values(result, use_evaluations)
    is_ga = result.algorithm is AlgorithmKind.GENETIC_ALGORITHM
    fig = go.Figure()

    if result.algorithm is AlgorithmKind.RANDOM_RESTART:
        groups: dict[int, list[tuple[int, object]]] = defaultdict(list)
        for x_value, point in zip(x_values, points):
            if point.restart is not None:
                groups[point.restart].append((x_value, point))
        palette = ["#2563EB", "#EA580C", "#0D9488", "#7C3AED", "#DB2777", "#65A30D"]
        best_restart = next(
            (
                point.restart
                for point in points
                if point.restart is not None and point.objective == result.best_objective
            ),
            None,
        )
        for index, (restart, entries) in enumerate(sorted(groups.items())):
            fig.add_trace(
                go.Scatter(
                    x=[entry[0] for entry in entries],
                    y=[entry[1].objective for entry in entries],
                    mode="lines+markers",
                    name=f"Restart {restart}" + (" · terbaik" if restart == best_restart else ""),
                    line={"color": palette[index % len(palette)], "width": 2},
                    marker={"size": 5},
                )
            )
        for restart in sorted(groups)[1:]:
            x_start = groups[restart][0][0]
            fig.add_vline(x=x_start, line_dash="dot", line_color="#94A3B8", opacity=0.7)
        if best_restart is not None:
            best_point = next(
                point for point in points
                if point.restart == best_restart and point.objective == result.best_objective
            )
            best_x = next(
                x for x, point in zip(x_values, points) if point is best_point
            )
            fig.add_trace(go.Scatter(
                x=[best_x], y=[best_point.objective], mode="markers",
                name="Best restart", marker={"color": "#111827", "size": 12, "symbol": "star"},
            ))
    else:
        fig.add_trace(
            go.Scatter(
                x=x_values,
                y=[point.objective for point in points],
                mode="lines+markers",
                name="Maksimum fitness" if is_ga else "Objective saat ini",
                line={"color": "#2563EB", "width": 3},
                marker={"size": 6},
            )
        )
        mean_values = [point.population_mean_objective for point in points]
        if is_ga and any(value is not None for value in mean_values):
            fig.add_trace(
                go.Scatter(
                    x=x_values, y=mean_values, mode="lines+markers",
                    name="Rata-rata fitness populasi",
                    line={"color": "#EA580C", "width": 3, "dash": "dash"},
                    marker={"size": 5},
                )
            )
        fig.add_trace(
            go.Scatter(
                x=x_values,
                y=[point.best_objective for point in points],
                mode="lines",
                name="Global best" if is_ga else "Best-so-far",
                line={"color": "#0D9488", "width": 2, "dash": "dash"},
            )
        )

    if result.algorithm is AlgorithmKind.SIMULATED_ANNEALING:
        accepted = [point for point in points if point.accepted is True]
        rejected = [point for point in points if point.accepted is False]
        for label, decisions, color, symbol in (
            ("Move diterima", accepted, "#16A34A", "circle"),
            ("Move ditolak", rejected, "#DC2626", "x"),
        ):
            if decisions:
                fig.add_trace(go.Scatter(
                    x=[_x_values(result, use_evaluations)[points.index(point)] for point in decisions],
                    y=[point.objective for point in decisions], mode="markers", name=label,
                    marker={"color": color, "size": 9, "symbol": symbol},
                ))

    x_title = "Objective evaluations" if use_evaluations else ("Generasi" if is_ga else "Iterasi")
    return _base_layout(fig, x_title=x_title, y_title="Nilai objective / fitness")


def _make_png(fig: go.Figure) -> bytes:
    """Render chart data to PNG using the project's existing Matplotlib dependency."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    data = fig.to_dict()
    figure, axis = plt.subplots(figsize=(9, 4.5), constrained_layout=True)
    for trace in data.get("data", []):
        x, y = trace.get("x", []), trace.get("y", [])
        if not x or not y:
            continue
        line = trace.get("line", {})
        marker = trace.get("marker", {})
        linestyle = {"dash": "--", "dot": ":", "dashdot": "-.", "solid": "-"}.get(line.get("dash"), "-")
        mode = trace.get("mode", "lines")
        axis.plot(
            x, y,
            label=trace.get("name"),
            color=line.get("color", marker.get("color")),
            linewidth=line.get("width", 2),
            linestyle=linestyle if "lines" in mode else "None",
            marker="o" if "markers" in mode else None,
            markersize=marker.get("size", 5),
        )
    layout = data.get("layout", {})
    axis.set_title(layout.get("title", {}).get("text", ""))
    axis.set_xlabel(layout.get("xaxis", {}).get("title", {}).get("text", ""))
    axis.set_ylabel(layout.get("yaxis", {}).get("title", {}).get("text", ""))
    if layout.get("yaxis", {}).get("type") == "log":
        axis.set_yscale("log")
    axis.grid(alpha=0.25)
    if any(trace.get("name") for trace in data.get("data", [])):
        axis.legend(loc="best", fontsize="small")
    output = BytesIO()
    figure.savefig(output, format="png", dpi=150)
    plt.close(figure)
    return output.getvalue()


def _render_chart(fig: go.Figure, *, key: str, download_name: str) -> None:
    st.plotly_chart(fig, width="stretch", key=key, config={"displaylogo": False})
    st.download_button(
        "Unduh grafik PNG",
        data=_make_png(fig),
        file_name=download_name,
        mime="image/png",
        key=f"{key}_png",
    )


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
    use_evaluations = axis_mode == "Evaluasi"
    _render_chart(
        make_objective_figure(result, use_evaluations=use_evaluations),
        key="objective_trace",
        download_name=f"{result.algorithm.value}-objective.png",
    )

    if result.algorithm is AlgorithmKind.SIDEWAYS:
        points = result.trace
        x = [point.step for point in points]
        moves = [point for point in points if point.accepted is True and point.delta == 0]
        fig = go.Figure(go.Scatter(
            x=x, y=[point.sideways_moves or 0 for point in points],
            mode="lines+markers", name="Sideways move kumulatif",
            line={"color": "#7C3AED", "width": 2},
        ))
        resets = [
            point for previous, point in zip(points, points[1:])
            if (previous.sideways_moves or 0) > 0 and point.sideways_moves == 0
        ]
        for label, marked, color, symbol in (
            ("Sideways move", moves, "#EA580C", "diamond"),
            ("Counter reset", resets, "#DC2626", "x"),
        ):
            if marked:
                fig.add_trace(go.Scatter(
                    x=[point.step for point in marked],
                    y=[point.sideways_moves or 0 for point in marked],
                    mode="markers", name=label,
                    marker={"color": color, "size": 10, "symbol": symbol},
                ))
        _render_chart(_base_layout(fig, x_title="Iterasi", y_title="Jumlah sideways move", height=300),
                      key="sideways_count", download_name="sideways-count.png")

    if any(point.accept_prob is not None for point in result.trace):
        if result.algorithm is AlgorithmKind.STOCHASTIC:
            probability_label = "Probabilitas pemilihan uphill move"
        else:
            probability_label = "Probabilitas penerimaan SA: e^(ΔE/T)"
        probability_points = [point for point in result.trace if point.accept_prob is not None]
        probability = go.Figure(go.Scatter(
            x=[point.step for point in probability_points],
            y=[point.accept_prob for point in probability_points],
            mode="lines+markers", name=probability_label,
            line={"color": "#EA580C", "width": 2},
        ))
        if result.algorithm is AlgorithmKind.SIMULATED_ANNEALING:
            for label, accepted, color, symbol in (
                ("Diterima", True, "#16A34A", "circle"),
                ("Ditolak", False, "#DC2626", "x"),
            ):
                marked = [point for point in probability_points if point.accepted is accepted]
                if marked:
                    probability.add_trace(go.Scatter(
                        x=[point.step for point in marked],
                        y=[point.accept_prob for point in marked],
                        mode="markers", name=label,
                        marker={"color": color, "size": 9, "symbol": symbol},
                    ))
        probability.update_layout(yaxis_range=[0, 1])
        _render_chart(_base_layout(probability, x_title="Iterasi", y_title=probability_label, height=300),
                      key="move_probability", download_name=f"{result.algorithm.value}-probability.png")

    if result.algorithm is AlgorithmKind.SIMULATED_ANNEALING and any(
        point.temperature is not None for point in result.trace
    ):
        temperature_points = [point for point in result.trace if point.temperature is not None]
        temperature = go.Figure(go.Scatter(
            x=[point.step for point in temperature_points],
            y=[point.temperature for point in temperature_points],
            mode="lines+markers", name="Temperatur",
            line={"color": "#7C3AED", "width": 3},
        ))
        stuck_points = [point for point in temperature_points if point.stuck is True]
        if stuck_points:
            temperature.add_trace(go.Scatter(
                x=[point.step for point in stuck_points],
                y=[point.temperature for point in stuck_points],
                mode="markers", name="Awal episode stuck",
                marker={"color": "#DC2626", "size": 10, "symbol": "x"},
            ))
        temperature.update_yaxes(type="log")
        _render_chart(_base_layout(temperature, x_title="Iterasi", y_title="Temperatur", height=320),
                      key="sa_temperature", download_name="simulated-annealing-temperature.png")
        st.metric("Episode stuck", sum(point.stuck is True for point in result.trace))

    st.caption("Data grafik juga tersedia sebagai tabel; nilainya berasal dari trajectory run ini.")
    st.dataframe(pd.DataFrame(result.trace_rows()), hide_index=True, width="stretch")


__all__ = ["make_objective_figure", "render_trace"]
