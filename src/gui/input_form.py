from __future__ import annotations

import json
from typing import Any

import pandas as pd
import streamlit as st

from domain.model import ObjectiveKind
from search.run import AlgorithmKind, RunConfig


ALGORITHM_LABELS = {
    AlgorithmKind.STEEPEST_ASCENT: "Hill Climbing · Steepest Ascent",
    AlgorithmKind.SIDEWAYS: "Hill Climbing · Sideways",
    AlgorithmKind.STOCHASTIC: "Hill Climbing · Stochastic",
    AlgorithmKind.RANDOM_RESTART: "Hill Climbing · Random Restart",
    AlgorithmKind.SIMULATED_ANNEALING: "Simulated Annealing",
    AlgorithmKind.GENETIC_ALGORITHM: "Genetic Algorithm",
}

OBJECTIVE_LABELS = {
    ObjectiveKind.TOTAL_VALUE: "Total value",
    ObjectiveKind.VALUE_PER_URGENCY: "Urgency-adjusted value",
}

ALGORITHM_HELP = {
    AlgorithmKind.STEEPEST_ASCENT: "Memilih feasible neighbor dengan peningkatan terbesar.",
    AlgorithmKind.SIDEWAYS: "Mengizinkan perpindahan bernilai sama untuk keluar dari plateau.",
    AlgorithmKind.STOCHASTIC: "Memilih secara acak dari uphill moves berdasarkan steepness.",
    AlgorithmKind.RANDOM_RESTART: "Menjalankan steepest-ascent dari beberapa initial state.",
    AlgorithmKind.SIMULATED_ANNEALING: "Sesekali menerima downhill move berdasarkan temperatur.",
    AlgorithmKind.GENETIC_ALGORITHM: "Mengembangkan populasi dengan seleksi, crossover, dan mutasi.",
}


def truck_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": truck["id"],
            "width": truck["dimensions"]["width"],
            "length": truck["dimensions"]["length"],
            "height": truck["dimensions"]["height"],
            "max_capacity": truck["max_capacity"],
        }
        for truck in data["trucks"]
    ]


def package_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": package["id"],
            "width": package["dimensions"]["width"],
            "length": package["dimensions"]["length"],
            "height": package["dimensions"]["height"],
            "value": package["value"],
            "weight": package["weight"],
            "is_fragile": package["is_fragile"],
            "eta": package["eta"],
        }
        for package in data["packages"]
    ]


def rows_to_problem_data(
    trucks: list[dict[str, Any]], packages: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "trucks": [
            {
                "id": row["id"],
                "dimensions": {
                    "width": row["width"],
                    "length": row["length"],
                    "height": row["height"],
                },
                "max_capacity": row["max_capacity"],
            }
            for row in trucks
        ],
        "packages": [
            {
                "id": row["id"],
                "dimensions": {
                    "width": row["width"],
                    "length": row["length"],
                    "height": row["height"],
                },
                "value": row["value"],
                "weight": row["weight"],
                "is_fragile": row["is_fragile"],
                "eta": row["eta"],
            }
            for row in packages
        ],
    }


def render_problem_editor(draft: dict[str, Any], version: int) -> dict[str, Any]:
    truck_tab, package_tab = st.tabs(
        [f"Truk · {len(draft['trucks'])}", f"Paket · {len(draft['packages'])}"]
    )
    with truck_tab:
        trucks = st.data_editor(
            pd.DataFrame(
                truck_rows(draft),
                columns=["id", "width", "length", "height", "max_capacity"],
            ),
            key=f"trucks_{version}",
            hide_index=True,
            num_rows="dynamic",
            width="stretch",
            height=max(160, min(360, 70 + 35 * len(draft["trucks"]))),
            column_config={
                "id": st.column_config.TextColumn("ID", required=True),
                "width": st.column_config.NumberColumn("Lebar", min_value=1, step=1, required=True),
                "length": st.column_config.NumberColumn("Panjang", min_value=1, step=1, required=True),
                "height": st.column_config.NumberColumn("Tinggi", min_value=1, step=1, required=True),
                "max_capacity": st.column_config.NumberColumn("Kapasitas", min_value=0.01, required=True),
            },
        )

    with package_tab:
        packages = st.data_editor(
            pd.DataFrame(
                package_rows(draft),
                columns=["id", "width", "length", "height", "value", "weight", "is_fragile", "eta"],
            ),
            key=f"packages_{version}",
            hide_index=True,
            num_rows="dynamic",
            width="stretch",
            height=max(220, min(470, 70 + 35 * len(draft["packages"]))),
            column_config={
                "id": st.column_config.TextColumn("ID", required=True),
                "width": st.column_config.NumberColumn("Lebar", min_value=1, step=1, required=True),
                "length": st.column_config.NumberColumn("Panjang", min_value=1, step=1, required=True),
                "height": st.column_config.NumberColumn("Tinggi", min_value=1, step=1, required=True),
                "value": st.column_config.NumberColumn("Value", min_value=0.0, required=True),
                "weight": st.column_config.NumberColumn("Berat", min_value=0.0, required=True),
                "is_fragile": st.column_config.CheckboxColumn("Fragile"),
                "eta": st.column_config.NumberColumn("ETA", min_value=0, step=1, required=True),
            },
        )

    truck_records = json.loads(trucks.to_json(orient="records"))
    package_records = json.loads(packages.to_json(orient="records"))
    return rows_to_problem_data(truck_records, package_records)


def render_run_config() -> RunConfig:
    st.markdown("### Pencarian")
    algorithm = st.selectbox(
        "Algoritma",
        list(AlgorithmKind),
        format_func=lambda item: ALGORITHM_LABELS.get(
            item, item.value.replace("_", " ").title()
        ),
        help="Pilih strategi pencarian yang akan dijalankan.",
    )
    objective = st.selectbox(
        "Objective",
        list(ObjectiveKind),
        format_func=lambda item: OBJECTIVE_LABELS[item],
        help="Urgency-adjusted value = Σ value / (ETA + 1).",
    )
    seed = st.number_input(
        "Seed",
        value=42,
        step=1,
        help="Bilangan acak awal agar run dapat direproduksi.",
    )
    max_evaluations = st.number_input(
        "Batas evaluasi",
        min_value=1,
        value=50_000,
        step=1_000,
        help="Jumlah maksimum evaluasi objective.",
    )
    values: dict[str, Any] = {
        "algorithm": algorithm,
        "objective": objective,
        "seed": int(seed),
        "max_evaluations": int(max_evaluations),
    }

    if algorithm is not AlgorithmKind.STEEPEST_ASCENT:
        with st.expander("Parameter algoritma", expanded=True):
            if algorithm is AlgorithmKind.SIDEWAYS:
                values["max_sideways"] = int(
                    st.number_input("Maksimum sideways move", min_value=0, value=100)
                )
            elif algorithm is AlgorithmKind.STOCHASTIC:
                values["max_iterations"] = int(
                    st.number_input("Maksimum iterasi", min_value=0, value=10_000)
                )
            elif algorithm is AlgorithmKind.RANDOM_RESTART:
                values["num_restarts"] = int(
                    st.number_input("Maksimum restart", min_value=0, value=10)
                )
            elif algorithm is AlgorithmKind.SIMULATED_ANNEALING:
                values["max_iterations"] = int(
                    st.number_input("Maksimum iterasi", min_value=0, value=10_000)
                )
                values["t_min"] = st.number_input(
                    "Temperatur minimum", min_value=0.000001, value=0.001, format="%.6f"
                )
                values["calibration_samples"] = int(
                    st.number_input("Sampel kalibrasi", min_value=0, value=100)
                )
            elif algorithm is AlgorithmKind.GENETIC_ALGORITHM:
                values["population_size"] = int(
                    st.number_input("Jumlah populasi", min_value=1, value=50)
                )
                values["generations"] = int(
                    st.number_input("Jumlah generasi", min_value=1, value=100)
                )
                values["crossover_prob"] = st.slider(
                    "Peluang crossover",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.9,
                    step=0.05,
                )
                use_default_mutation = st.checkbox(
                    "Mutasi default (0,2)",
                    value=True,
                    help="Peluang mutasi diterapkan per anak.",
                )
                if not use_default_mutation:
                    values["mutation_prob"] = st.slider(
                        "Peluang mutasi",
                        min_value=0.0,
                        max_value=1.0,
                        value=0.2,
                        step=0.01,
                    )

    return RunConfig(**values)


__all__ = [
    "ALGORITHM_HELP",
    "ALGORITHM_LABELS",
    "OBJECTIVE_LABELS",
    "package_rows",
    "render_problem_editor",
    "render_run_config",
    "rows_to_problem_data",
    "truck_rows",
]
