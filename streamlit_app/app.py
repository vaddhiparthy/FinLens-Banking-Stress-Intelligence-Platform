# ruff: noqa: E402

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").exists()
)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from finlens.pipeline_status import pipeline_status_rows
from streamlit_app.lib.data import load_failures, load_metrics, load_stress_pulse
from streamlit_app.lib.page_shell import status_ribbon
from streamlit_app.lib.telemetry import record_page_view
from streamlit_app.lib.theme import app_css, ensure_theme_state, get_theme_mode
from streamlit_app.lib.ui_components import (
    inject_styles,
    metric_card,
    section_heading,
    styled_table,
)


def _data_summary() -> pd.DataFrame:
    failures = load_failures()
    metrics = load_metrics()
    stress = load_stress_pulse()
    series_count = metrics["series_id"].nunique() if not metrics.empty else 0
    return pd.DataFrame(
        [
            {
                "Domain": "Bank failure history",
                "Current loaded asset": f"{len(failures):,} FDIC failure records",
                "What it supports": (
                    "Failure concentration, acquirer analysis, and filtered institution inventory"
                ),
            },
            {
                "Domain": "Industry stress pulse",
                "Current loaded asset": f"{len(stress):,} aggregate reporting periods",
                "What it supports": (
                    "Net income, ROA, NIM, asset quality, and source-aware unavailable states"
                ),
            },
            {
                "Domain": "Macro context",
                "Current loaded asset": f"{series_count:,} FRED series",
                "What it supports": (
                    "Yield curve, labor, inflation, housing, and macro-to-failure context"
                ),
            },
            {
                "Domain": "Engineering control plane",
                "Current loaded asset": f"{len(pipeline_status_rows())} live pipeline movements",
                "What it supports": (
                    "Source-to-bronze, bronze-to-silver, silver-to-gold, and serving status"
                ),
            },
        ]
    )


def _surface_summary() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Surface": "Business",
                "Primary audience": "Banking, risk, and executive reviewers",
                "What they see": (
                    "Industry stress, failure forensics, macro context, and business glossary"
                ),
            },
            {
                "Surface": "Technical",
                "Primary audience": "Data engineering and architecture reviewers",
                "What they see": (
                    "Pipeline status, data classification, reconciliation, run results, "
                    "and administration"
                ),
            },
        ]
    )


st.set_page_config(
    page_title="FinLens | Banking Stress Intelligence",
    layout="wide",
    initial_sidebar_state="collapsed",
)
ensure_theme_state()
inject_styles(app_css(get_theme_mode(), sidebar_open=False))
record_page_view("home", "landing")

st.markdown(
    """
    <div class="home-center-brand">
        <span class="topbar-mark edge-mark">FL</span>
        <span class="home-center-copy">
            <span class="edge-title">FinLens</span>
            <span class="edge-subtitle">Banking stress intelligence</span>
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="home-hero">
        <div class="home-kicker">FinLens</div>
        <div class="home-title">FinLens Banking Stress Intelligence</div>
        <div class="home-copy">
            A public-data banking intelligence platform that converts FDIC, FRED, QBP-style
            aggregates, institution metadata, and pipeline telemetry into governed business
            dashboards and a transparent data-engineering control surface.
        </div>
        <div class="home-subcopy">
            The product is organized as two complementary lenses: a business surface for
            interpreting banking stress and a technical surface for inspecting how the data
            is sourced, transformed, validated, and served.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
status_ribbon("Public banking data platform")

card1, card2, card3, card4 = st.columns(4)
failures = load_failures()
metrics = load_metrics()
stress = load_stress_pulse()
pipeline_rows = pipeline_status_rows()
with card1:
    metric_card("FDIC failures", f"{len(failures):,}", "Loaded public failure records")
with card2:
    metric_card("Stress periods", f"{len(stress):,}", "Aggregate banking periods")
with card3:
    metric_card(
        "FRED series",
        f"{metrics['series_id'].nunique() if not metrics.empty else 0:,}",
        "Macro indicators normalized",
    )
with card4:
    metric_card("Pipeline flows", f"{len(pipeline_rows)}", "Tracked data movements")

left, right = st.columns([1, 1], vertical_alignment="center")
with left:
    section_heading(
        "Executive Overview",
        "FinLens is built to show both sides of a serious data product: the business questions "
        "answered by the analytics and the engineering controls that make those analytics "
        "traceable. It starts with public, stable banking sources, lands them as raw artifacts, "
        "normalizes them into canonical tables, and exposes only dashboard-ready marts.",
    )
    styled_table(_surface_summary())
with right:
    section_heading(
        "What Is Active",
        "The current product surfaces live public data and runtime status without filling source "
        "gaps with invented values.",
    )
    styled_table(_data_summary())

action_left, action_middle, action_right = st.columns([1.2, 1, 1.2], vertical_alignment="center")
with action_left:
    if st.button(
        "Open Technical Surface",
        key="home_open_technical",
        use_container_width=True,
    ):
        st.session_state["technical_section"] = "pipeline"
        st.switch_page("pages/4_Under_The_Hood.py")
with action_middle:
    st.markdown('<div class="home-action-divider">Choose a surface</div>', unsafe_allow_html=True)
with action_right:
    if st.button(
        "Open Business Surface",
        key="home_open_business",
        use_container_width=True,
    ):
        st.switch_page("pages/0_Stress_Pulse.py")

section_heading(
    "How The Platform Is Organized",
    "Business pages explain the banking story. Technical pages expose the source contracts, "
    "table inventory, transformation rules, run results, and operational controls behind that "
    "story.",
)

st.markdown(
    """
    <div class="home-credit">
        <div class="home-credit-kicker">By</div>
        <div class="home-credit-name">Sri Surya S. Vaddhiparthy</div>
        <div class="home-credit-meta">M.S. (Data Science)</div>
        <div class="home-credit-link">surya.vaddhiparthy.com</div>
    </div>
    """,
    unsafe_allow_html=True,
)
