from __future__ import annotations

from html import escape

import streamlit as st


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #172033;
            --muted: #687386;
            --line: #E5E9F0;
            --surface: #FFFFFF;
            --surface-soft: #F7F8FA;
            --brand: #315CF4;
            --brand-dark: #2444C7;
            --accent: #12A594;
            --radius: 18px;
        }

        html, body, [class*="css"], .stApp {
            font-family: "Aptos", "Segoe UI Variable Text", "Inter", sans-serif;
            color: var(--ink);
        }
        .stApp { background: #FAFBFC; }
        .block-container {
            max-width: 1240px;
            padding-top: 1.6rem;
            padding-bottom: 3rem;
        }
        h1, h2, h3, .workspace-title, .setup-title {
            font-family: "Aptos Display", "Segoe UI Variable Display", "Inter", sans-serif;
            letter-spacing: -0.035em;
        }

        [data-testid="stSidebar"] {
            background: #F4F6F9;
            border-right: 1px solid var(--line);
        }
        [data-testid="stSidebar"] .block-container { padding-top: 1.35rem; }
        [data-testid="stSidebar"] h3 { margin-top: .4rem; }

        .workspace-header {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 1rem;
            padding: .4rem 0 1.45rem;
            border-bottom: 1px solid var(--line);
            margin-bottom: 1.5rem;
        }
        .workspace-eyebrow {
            color: var(--brand);
            font-size: .72rem;
            font-weight: 750;
            letter-spacing: .14em;
            text-transform: uppercase;
            margin-bottom: .35rem;
        }
        .workspace-title {
            color: var(--ink);
            font-size: clamp(2rem, 4vw, 3.15rem);
            font-weight: 760;
            line-height: 1;
            margin: 0;
        }
        .workspace-subtitle {
            color: var(--muted);
            font-size: .96rem;
            margin: .55rem 0 0;
        }
        .workspace-badge {
            background: #EEF2FF;
            border: 1px solid #DDE4FF;
            border-radius: 999px;
            color: var(--brand-dark);
            font-size: .78rem;
            font-weight: 700;
            padding: .5rem .8rem;
            white-space: nowrap;
        }
        .sidebar-brand {
            display: flex;
            align-items: center;
            gap: .7rem;
            margin: .15rem 0 1.2rem;
        }
        .brand-mark {
            display: grid;
            place-items: center;
            width: 2.15rem;
            height: 2.15rem;
            border-radius: 11px;
            background: var(--brand);
            color: white;
            font-weight: 800;
            box-shadow: 0 7px 18px rgba(49, 92, 244, .22);
        }
        .brand-name { font-size: 1.05rem; font-weight: 760; line-height: 1.1; }
        .brand-meta { color: var(--muted); font-size: .72rem; margin-top: .15rem; }

        .section-heading { margin: 1.7rem 0 .85rem; }
        .section-heading:first-child { margin-top: 0; }
        .section-index {
            color: var(--brand);
            font-size: .7rem;
            font-weight: 800;
            letter-spacing: .12em;
            text-transform: uppercase;
            margin-bottom: .2rem;
        }
        .section-title {
            color: var(--ink);
            font-size: 1.5rem;
            font-weight: 720;
            letter-spacing: -.025em;
            line-height: 1.2;
        }

        .setup-strip {
            display: grid;
            grid-template-columns: minmax(240px, 2fr) repeat(3, minmax(110px, 1fr));
            gap: 0;
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: var(--radius);
            box-shadow: 0 8px 28px rgba(23, 32, 51, .05);
            overflow: hidden;
            margin-bottom: 1rem;
        }
        .setup-cell { min-width: 0; padding: 1rem 1.15rem; }
        .setup-cell + .setup-cell { border-left: 1px solid var(--line); }
        .setup-label {
            color: var(--muted);
            font-size: .7rem;
            font-weight: 700;
            letter-spacing: .06em;
            text-transform: uppercase;
        }
        .setup-title, .setup-value {
            color: var(--ink);
            font-weight: 720;
            line-height: 1.18;
            margin-top: .32rem;
            overflow-wrap: anywhere;
        }
        .setup-title { font-size: clamp(1.1rem, 2vw, 1.45rem); }
        .setup-value { font-size: 1.02rem; }

        .inline-success {
            background: #ECFDF3;
            border: 1px solid #ABEFC6;
            border-radius: 12px;
            color: #067647;
            font-size: .92rem;
            font-weight: 700;
            margin: .2rem 0 .9rem;
            padding: .78rem 1rem;
        }

        [data-testid="stMetric"] {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: .8rem .9rem;
            box-shadow: none;
            min-width: 0;
        }
        [data-testid="stMetricLabel"] { color: var(--muted); }
        [data-testid="stMetricValue"] {
            color: var(--ink);
            font-size: clamp(1.25rem, 2vw, 1.8rem);
            font-variant-numeric: tabular-nums;
            overflow-wrap: anywhere;
        }

        [data-testid="stVerticalBlockBorderWrapper"] {
            border-color: var(--line) !important;
            border-radius: var(--radius) !important;
        }
        [data-testid="stDataFrame"], [data-testid="stPlotlyChart"] {
            border: 1px solid var(--line);
            border-radius: 16px;
            overflow: hidden;
        }
        [data-baseweb="tab-list"] {
            gap: .35rem;
            border-bottom: 1px solid var(--line);
        }
        [data-baseweb="tab"] {
            border-radius: 10px 10px 0 0;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        .stButton > button, .stDownloadButton > button {
            border-radius: 11px;
            font-weight: 700;
            min-height: 2.7rem;
        }
        div[data-testid="stAlert"] { border-radius: 14px; }
        hr { border-color: var(--line); }

        @media (max-width: 900px) {
            .setup-strip { grid-template-columns: 1fr 1fr; }
            .setup-cell:nth-child(3) { border-left: 0; border-top: 1px solid var(--line); }
            .setup-cell:nth-child(4) { border-top: 1px solid var(--line); }
            .workspace-badge { display: none; }
        }
        @media (max-width: 560px) {
            .setup-strip { grid-template-columns: 1fr; }
            .setup-cell + .setup-cell { border-left: 0; border-top: 1px solid var(--line); }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_brand() -> None:
    st.markdown(
        """
        <div class="sidebar-brand">
            <div class="brand-mark">CL</div>
            <div><div class="brand-name">Cargo Lab</div><div class="brand-meta">IF3170 · Local Search</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(*, mode: str) -> None:
    badge = "Single run" if mode == "Single Run" else "Experiments"
    st.markdown(
        f"""
        <div class="workspace-header">
            <div>
                <div class="workspace-eyebrow">3D knapsack optimizer</div>
                <h1 class="workspace-title">Cargo Lab</h1>
                <p class="workspace-subtitle">Rancang muatan, jalankan local search, dan telaah hasilnya.</p>
            </div>
            <div class="workspace-badge">{badge}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section(index: str, title: str) -> None:
    st.markdown(
        f"""
        <div class="section-heading">
            <div class="section-index">{escape(index)}</div>
            <div class="section-title">{escape(title)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_setup_strip(
    *, algorithm: str, objective: str, seed: int, budget: int
) -> None:
    st.markdown(
        f"""
        <div class="setup-strip">
            <div class="setup-cell">
                <div class="setup-label">Algoritma</div>
                <div class="setup-title">{escape(algorithm)}</div>
            </div>
            <div class="setup-cell">
                <div class="setup-label">Objective</div>
                <div class="setup-value">{escape(objective)}</div>
            </div>
            <div class="setup-cell">
                <div class="setup-label">Seed</div>
                <div class="setup-value">{seed:,}</div>
            </div>
            <div class="setup-cell">
                <div class="setup-label">Budget</div>
                <div class="setup-value">{budget:,}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_success(message: str) -> None:
    st.markdown(
        f'<div class="inline-success">{escape(message)}</div>',
        unsafe_allow_html=True,
    )


__all__ = [
    "apply_theme",
    "render_page_header",
    "render_section",
    "render_setup_strip",
    "render_sidebar_brand",
    "render_success",
]
