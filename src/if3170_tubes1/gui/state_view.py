from __future__ import annotations

import hashlib
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..domain.model import ObjectiveKind, Problem, State, Truck
from ..domain.objectives import summarize_state


PACKAGE_COLORS = (
    "#2563EB",
    "#EA580C",
    "#0D9488",
    "#7C3AED",
    "#D97706",
    "#0891B2",
    "#BE185D",
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
    x: int, y: int, z: int, width: int, length: int, height: int
) -> tuple[tuple[int, int, int], ...]:
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


def _edge_trace(vertices: tuple[tuple[int, int, int], ...], color: str, width: int) -> go.Scatter3d:
    coordinates = [[], [], []]
    for start, end in BOX_EDGES:
        for axis in range(3):
            coordinates[axis].extend((vertices[start][axis], vertices[end][axis], None))
    return go.Scatter3d(
        x=coordinates[0], y=coordinates[1], z=coordinates[2],
        mode="lines", line={"color": color, "width": width},
        hoverinfo="skip", showlegend=False,
    )


def _package_color(package_id: str) -> str:
    digest = hashlib.blake2b(package_id.encode("utf-8"), digest_size=2).digest()
    return PACKAGE_COLORS[int.from_bytes(digest, "big") % len(PACKAGE_COLORS)]


def make_truck_figure(problem: Problem, state: State, truck: Truck) -> go.Figure:
    fig = go.Figure()
    outline = box_vertices(
        0, 0, 0,
        truck.dimensions.width,
        truck.dimensions.length,
        truck.dimensions.height,
    )
    fig.add_trace(_edge_trace(outline, "#64748B", 5))

    for placement in state.placements:
        if placement.truck_id != truck.id or placement.position is None:
            continue
        package = problem.package(placement.package_id)
        size = package.dimensions.oriented(placement.orientation)
        vertices = box_vertices(
            placement.position.x, placement.position.y, placement.position.z,
            size.width, size.length, size.height,
        )
        color = _package_color(package.id)
        hover = (
            f"<b>{escape(package.id)}</b><br>Posisi: "
            f"({placement.position.x}, {placement.position.y}, {placement.position.z})"
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
                opacity=0.82,
                flatshading=True,
                name=f"{package.id}{' · Fragile' if package.is_fragile else ''}",
                hovertext=hover,
                hoverinfo="text",
                showlegend=True,
            )
        )
        fig.add_trace(_edge_trace(vertices, "#B91C1C" if package.is_fragile else "#334155", 4))

    fig.update_layout(
        height=510,
        margin={"l": 0, "r": 0, "t": 8, "b": 0},
        paper_bgcolor="#FFFFFF",
        font={"color": "#15243B"},
        legend={"orientation": "h", "y": -0.08, "x": 0},
        scene={
            "xaxis": {"title": "Lebar (x)", "range": [0, truck.dimensions.width], "backgroundcolor": "#F8FAFC"},
            "yaxis": {"title": "Panjang (y)", "range": [0, truck.dimensions.length], "backgroundcolor": "#F8FAFC"},
            "zaxis": {"title": "Tinggi (z)", "range": [0, truck.dimensions.height], "backgroundcolor": "#F8FAFC"},
            "aspectmode": "data",
            "camera": {"eye": {"x": 1.5, "y": 1.4, "z": 1.0}},
        },
    )
    return fig


def render_state(
    problem: Problem, state: State, objective: ObjectiveKind, *, key: str
) -> None:
    summary = summarize_state(problem, state, objective)
    metrics = st.columns(4)
    metrics[0].metric("Objective", f"{summary['objective']:,.2f}")
    metrics[1].metric("Total value", f"{summary['total_value']:,.2f}")
    metrics[2].metric("Di dalam", summary["inside_count"])
    metrics[3].metric("Di luar", summary["outside_count"])

    tabs = st.tabs([truck.id for truck in problem.trucks])
    for tab, truck in zip(tabs, problem.trucks):
        with tab:
            details = summary["trucks"][truck.id]
            st.caption(
                f"{details['package_count']} paket · Berat {details['weight']:g} / "
                f"{truck.max_capacity:g} · Value {details['value']:g}"
            )
            fig = make_truck_figure(problem, state, truck)
            st.plotly_chart(
                fig,
                width="stretch",
                key=f"{key}_{truck.id}",
                config={"displaylogo": False},
                alt=f"Susunan paket dalam truk {truck.id}. {details['package_count']} paket di dalam.",
            )
            if details["package_count"] == 0:
                st.info("Belum ada paket di truk ini.")

    outside = [
        problem.package(placement.package_id)
        for placement in state.placements
        if placement.is_outside
    ]
    st.markdown("#### Paket di luar armada")
    if outside:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "ID": package.id,
                        "Ukuran": f"{package.dimensions.width} × {package.dimensions.length} × {package.dimensions.height}",
                        "Value": package.value,
                        "Berat": package.weight,
                        "Fragile": "Ya" if package.is_fragile else "Tidak",
                    }
                    for package in outside
                ]
            ),
            hide_index=True,
            width="stretch",
        )
    else:
        st.success("Semua paket berada di dalam armada.")
