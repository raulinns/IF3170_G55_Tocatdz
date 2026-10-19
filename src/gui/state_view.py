from __future__ import annotations

import hashlib
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from domain.model import ObjectiveKind, Problem, State, Truck
from domain.objectives import summarize_state


PACKAGE_COLORS = (
    "#315CF4",
    "#F97316",
    "#12A594",
    "#8B5CF6",
    "#D99A14",
    "#0891B2",
    "#DB2777",
    "#4F46E5",
)
BOX_EDGES = (
    (0, 1), (1, 2), (2, 3), (3, 0),
    (4, 5), (5, 6), (6, 7), (7, 4),
    (0, 4), (1, 5), (2, 6), (3, 7),
)
BOX_FACES = (
    (0, 2, 1), (0, 3, 2),
    (4, 5, 6), (4, 6, 7),
    (0, 1, 5), (0, 5, 4),
    (3, 7, 6), (3, 6, 2),
    (0, 4, 7), (0, 7, 3),
    (1, 2, 6), (1, 6, 5),
)


def box_vertices(
    x: float, y: float, z: float, width: int, length: int, height: int
) -> tuple[tuple[float, float, float], ...]:
    return (
        (x, y, z),
        (x + width, y, z),
        (x + width, y + length, z),
        (x, y + length, z),
        (x, y, z + height),
        (x + width, y, z + height),
        (x + width, y + length, z + height),
        (x, y + length, z + height),
    )


def _edge_trace(
    vertices: tuple[tuple[float, float, float], ...], color: str, width: int
) -> go.Scatter3d:
    coordinates: list[list[float | None]] = [[], [], []]
    for start, end in BOX_EDGES:
        for axis in range(3):
            coordinates[axis].extend((vertices[start][axis], vertices[end][axis], None))
    return go.Scatter3d(
        x=coordinates[0],
        y=coordinates[1],
        z=coordinates[2],
        mode="lines",
        line={"color": color, "width": width},
        hoverinfo="skip",
        showlegend=False,
    )


def _package_color(package_id: str) -> str:
    digest = hashlib.blake2b(package_id.encode("utf-8"), digest_size=2).digest()
    return PACKAGE_COLORS[int.from_bytes(digest, "big") % len(PACKAGE_COLORS)]


def _aspect_ratio(width: float, length: float, height: float) -> dict[str, float]:
    largest = max(width, length, height, 1)
    return {
        "x": max(.45, width / largest),
        "y": max(.45, length / largest),
        "z": max(.45, height / largest),
    }


def _focus_button(
    label: str,
    *,
    x_range: list[float],
    y_range: list[float],
    z_range: list[float],
) -> dict[str, object]:
    return {
        "label": label,
        "method": "relayout",
        "args": [
            {
                "scene.xaxis.range": x_range,
                "scene.yaxis.range": y_range,
                "scene.zaxis.range": z_range,
                "scene.aspectratio": _aspect_ratio(
                    x_range[1] - x_range[0],
                    y_range[1] - y_range[0],
                    z_range[1] - z_range[0],
                ),
                "scene.camera": {"eye": {"x": 1.55, "y": 1.45, "z": 1.05}},
            }
        ],
    }


def make_fleet_figure(problem: Problem, state: State) -> go.Figure:
    """Gabungkan seluruh truk dalam satu scene dan sediakan tombol fokus."""
    fig = go.Figure()
    max_width = max(truck.dimensions.width for truck in problem.trucks)
    max_length = max(truck.dimensions.length for truck in problem.trucks)
    max_height = max(truck.dimensions.height for truck in problem.trucks)
    gap = max(2.0, max_width * .4)
    offset = 0.0
    focus_buttons: list[dict[str, object]] = []

    for truck in problem.trucks:
        width = truck.dimensions.width
        length = truck.dimensions.length
        height = truck.dimensions.height
        outline = box_vertices(offset, 0, 0, width, length, height)

        fig.add_trace(
            go.Mesh3d(
                x=[offset, offset + width, offset + width, offset],
                y=[0, 0, length, length],
                z=[0, 0, 0, 0],
                i=[0, 0],
                j=[1, 2],
                k=[2, 3],
                color="#DCE4F2",
                opacity=.35,
                hoverinfo="skip",
                showlegend=False,
            )
        )
        fig.add_trace(_edge_trace(outline, "#6B7890", 5))

        package_count = 0
        for placement in state.placements:
            if placement.truck_id != truck.id or placement.position is None:
                continue
            package_count += 1
            package = problem.package(placement.package_id)
            size = package.dimensions.oriented(placement.orientation)
            vertices = box_vertices(
                offset + placement.position.x,
                placement.position.y,
                placement.position.z,
                size.width,
                size.length,
                size.height,
            )
            color = _package_color(package.id)
            hover = (
                f"<b>{escape(package.id)}</b> · {escape(truck.id)}"
                f"<br>Posisi: ({placement.position.x}, {placement.position.y}, {placement.position.z})"
                f"<br>Ukuran: {size.width} × {size.length} × {size.height}"
                f"<br>Value: {package.value:g} · Berat: {package.weight:g}"
                f"<br>Fragile: {'Ya' if package.is_fragile else 'Tidak'}"
            )
            fig.add_trace(
                go.Mesh3d(
                    x=[vertex[0] for vertex in vertices],
                    y=[vertex[1] for vertex in vertices],
                    z=[vertex[2] for vertex in vertices],
                    i=[face[0] for face in BOX_FACES],
                    j=[face[1] for face in BOX_FACES],
                    k=[face[2] for face in BOX_FACES],
                    color=color,
                    opacity=.88,
                    flatshading=True,
                    hovertext=hover,
                    hoverinfo="text",
                    showlegend=False,
                )
            )
            fig.add_trace(
                _edge_trace(
                    vertices,
                    "#B42318" if package.is_fragile else "#25324A",
                    3,
                )
            )

        fig.add_trace(
            go.Scatter3d(
                x=[offset + width / 2],
                y=[length / 2],
                z=[height + max_height * .12],
                mode="text",
                text=[f"<b>{escape(truck.id)}</b> · {package_count} paket"],
                textfont={"color": "#172033", "size": 14},
                hoverinfo="skip",
                showlegend=False,
            )
        )
        focus_buttons.append(
            _focus_button(
                truck.id,
                x_range=[offset - .5, offset + width + .5],
                y_range=[-.5, length + .5],
                z_range=[0, height + max_height * .28],
            )
        )
        offset += width + gap

    total_width = max(1.0, offset - gap)
    all_ranges = {
        "x": [-.8, total_width + .8],
        "y": [-.8, max_length + .8],
        "z": [0, max_height * 1.3],
    }
    buttons = [
        _focus_button(
            "Semua",
            x_range=all_ranges["x"],
            y_range=all_ranges["y"],
            z_range=all_ranges["z"],
        ),
        *focus_buttons,
    ]
    fig.update_layout(
        height=570,
        margin={"l": 0, "r": 0, "t": 70, "b": 0},
        paper_bgcolor="#FFFFFF",
        font={
            "family": "Aptos, Segoe UI Variable Text, Inter, sans-serif",
            "color": "#172033",
        },
        showlegend=False,
        updatemenus=[
            {
                "type": "buttons",
                "direction": "right",
                "x": 0,
                "y": 1.12,
                "xanchor": "left",
                "yanchor": "top",
                "showactive": True,
                "active": 0,
                "bgcolor": "#F4F6F9",
                "bordercolor": "#DDE3EC",
                "font": {"color": "#25324A", "size": 12},
                "buttons": buttons,
            }
        ],
        scene={
            "xaxis": {
                "title": "Lebar (x)",
                "range": all_ranges["x"],
                "backgroundcolor": "#F8FAFC",
                "gridcolor": "#E2E8F0",
            },
            "yaxis": {
                "title": "Panjang (y)",
                "range": all_ranges["y"],
                "backgroundcolor": "#F8FAFC",
                "gridcolor": "#E2E8F0",
            },
            "zaxis": {
                "title": "Tinggi (z)",
                "range": all_ranges["z"],
                "backgroundcolor": "#F8FAFC",
                "gridcolor": "#E2E8F0",
            },
            "aspectmode": "manual",
            "aspectratio": _aspect_ratio(total_width, max_length, max_height),
            "camera": {"eye": {"x": 1.55, "y": 1.45, "z": 1.05}},
        },
    )
    return fig


def make_truck_figure(problem: Problem, state: State, truck: Truck) -> go.Figure:
    """Kompatibilitas untuk pemanggil lama; fokuskan fleet figure ke satu truk."""
    single_problem = Problem((truck,), problem.packages)
    return make_fleet_figure(single_problem, state)


def render_state(
    problem: Problem, state: State, objective: ObjectiveKind, *, key: str
) -> None:
    summary = summarize_state(problem, state, objective)
    metrics = st.columns(4)
    metrics[0].metric("Objective", f"{summary['objective']:,.2f}")
    metrics[1].metric("Total value", f"{summary['total_value']:,.2f}")
    metrics[2].metric("Paket masuk", summary["inside_count"])
    metrics[3].metric("Paket di luar", summary["outside_count"])

    figure = make_fleet_figure(problem, state)
    st.plotly_chart(
        figure,
        width="stretch",
        key=f"{key}_fleet",
        config={"displaylogo": False, "scrollZoom": True},
        alt="Visualisasi tiga dimensi seluruh armada dan paket yang ditempatkan.",
    )

    with st.expander("Detail muatan per truk"):
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Truk": truck.id,
                        "Paket": summary["trucks"][truck.id]["package_count"],
                        "Berat": summary["trucks"][truck.id]["weight"],
                        "Kapasitas": truck.max_capacity,
                        "Utilisasi berat": (
                            summary["trucks"][truck.id]["weight"]
                            / truck.max_capacity
                        ),
                        "Value": summary["trucks"][truck.id]["value"],
                    }
                    for truck in problem.trucks
                ]
            ),
            hide_index=True,
            width="stretch",
            column_config={
                "Utilisasi berat": st.column_config.ProgressColumn(
                    "Utilisasi berat", min_value=0.0, max_value=1.0, format="percent"
                )
            },
        )

    outside = [
        problem.package(placement.package_id)
        for placement in state.placements
        if placement.is_outside
    ]
    if outside:
        with st.expander(f"Paket di luar armada · {len(outside)}"):
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "ID": package.id,
                            "Ukuran": (
                                f"{package.dimensions.width} × "
                                f"{package.dimensions.length} × "
                                f"{package.dimensions.height}"
                            ),
                            "Value": package.value,
                            "Berat": package.weight,
                            "ETA": package.eta,
                            "Fragile": "Ya" if package.is_fragile else "Tidak",
                        }
                        for package in outside
                    ]
                ),
                hide_index=True,
                width="stretch",
            )


__all__ = ["box_vertices", "make_fleet_figure", "make_truck_figure", "render_state"]
