# ruff: noqa: E402

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").exists()
)
for sub in ("", "src", "ml"):
    p = str(PROJECT_ROOT / sub) if sub else str(PROJECT_ROOT)
    if p not in sys.path:
        sys.path.insert(0, p)

from finlens.pipeline_status import pipeline_status_rows
from streamlit_app.lib.data import load_failures, load_metrics, load_stress_pulse
from streamlit_app.lib.page_shell import home_navigation
from streamlit_app.lib.telemetry import record_page_view
from streamlit_app.lib.theme import app_css, ensure_theme_state, get_theme_mode
from streamlit_app.lib.ui_components import (
    chart_note,
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
                "Surface": "Data Engineering",
                "Primary audience": "Data engineering and architecture reviewers",
                "What they see": (
                    "Pipeline status, data classification, reconciliation, run results, "
                    "and administration"
                ),
            },
            {
                "Surface": "AI Engineering",
                "Primary audience": "ML engineering and model-risk reviewers",
                "What they see": (
                    "The bank-distress model end to end: pipeline, feature contract, stack, "
                    "out-of-time metrics, SHAP, drift, decisions, governance, and a live "
                    "predictive scenario tab"
                ),
            },
        ]
    )


st.set_page_config(
    page_title="FinLens: Regulatory-Grade Banking Data Platform",
    layout="wide",
    initial_sidebar_state="collapsed",
)
ensure_theme_state()
inject_styles(app_css(get_theme_mode(), sidebar_open=False))
record_page_view("home", "landing")


st.markdown(
    """
    <style>
    div[role="dialog"] {
        border-radius: 18px !important;
    }
    div[role="dialog"] button[aria-label="Close"] {
        display: none !important;
    }
    div[role="dialog"] [data-testid="stVerticalBlock"] {
        gap: .65rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.dialog("Important Use Notice", width="small", dismissible=False)
def _legal_disclaimer() -> None:
    st.markdown(
        """
        FinLens is a personal portfolio project built to demonstrate data engineering,
        public-data integration, and banking analytics presentation. It is not affiliated
        with or endorsed by any regulator or financial institution.

        Do not use this project as financial, investment, regulatory, or supervisory advice.
        For decisions about a bank, deposit, investment, or financial institution, rely only
        on official U.S. government and regulator sources.
        """,
    )
    if st.button("I understand", key="accept_home_disclaimer", use_container_width=True):
        st.session_state["home_disclaimer_accepted"] = True
        st.rerun()


if not st.session_state.get("home_disclaimer_accepted"):
    _legal_disclaimer()

home_navigation()

failures = load_failures()
metrics = load_metrics()
stress = load_stress_pulse()
pipeline_rows = pipeline_status_rows()
n_fred = metrics["series_id"].nunique() if not metrics.empty else 0

# Full-bleed hero (first person, short outcome headline, no boxed rectangle)
st.markdown(
    """
    <div class="landing-hero">
        <div class="landing-eyebrow">Surya Vaddhiparthy · M.S. Data Science</div>
        <div class="landing-h1">Spotting financial stress<br>in U.S. banks</div>
        <p class="landing-sub">
            FinLens turns free public banking data (FDIC Call Reports, failure
            history, FRED macro series) into an early-warning read on bank distress, and
            shows the full data-engineering and machine-learning build behind it.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Primary navigation: the three surfaces, above the fold
st.markdown('<div class="landing-pick">Pick where you want to start</div>', unsafe_allow_html=True)
ent_b, ent_d, ent_a = st.columns(3, vertical_alignment="top")
with ent_b:
    st.markdown(
        '<div class="surface-card surface-card-b">'
        '<div class="surface-card-k">Business</div>'
        '<div class="surface-card-t">Read the banking story</div>'
        '<div class="surface-card-c">Industry stress, bank-failure forensics, macro '
        'context, and a live distress scorer for any bank.</div></div>',
        unsafe_allow_html=True,
    )
    if st.button("Enter Business", key="home_open_business", use_container_width=True):
        st.switch_page("pages/0_Stress_Pulse.py")
with ent_d:
    st.markdown(
        '<div class="surface-card surface-card-d">'
        '<div class="surface-card-k">Data Engineering</div>'
        '<div class="surface-card-t">See how it is built</div>'
        '<div class="surface-card-c">The pipeline, source contracts, warehouse, data '
        'quality, and operations behind every number.</div></div>',
        unsafe_allow_html=True,
    )
    if st.button("Enter Data Engineering", key="home_open_de", use_container_width=True):
        st.session_state["technical_section"] = "pipeline"
        st.switch_page("pages/4_Data_Engineering.py")
with ent_a:
    st.markdown(
        '<div class="surface-card surface-card-a">'
        '<div class="surface-card-k">AI Engineering</div>'
        '<div class="surface-card-t">Look inside the model</div>'
        '<div class="surface-card-c">The calibrated distress model end to end: features, '
        'training, out-of-time metrics, SHAP, and drift.</div></div>',
        unsafe_allow_html=True,
    )
    if st.button("Enter AI Engineering", key="home_open_ai", use_container_width=True):
        st.switch_page("pages/7_AI_Engineering.py")

# Supporting content (scroll)
st.markdown('<div class="landing-section-rule"></div>', unsafe_allow_html=True)
st.markdown('<div class="landing-h2">What it is built on</div>', unsafe_allow_html=True)
card1, card2, card3, card4 = st.columns(4)
with card1:
    metric_card("FDIC failures", f"{len(failures):,}", "Public failure records")
with card2:
    metric_card("Stress periods", f"{len(stress):,}", "Aggregate banking quarters")
with card3:
    metric_card("FRED series", f"{n_fred:,}", "Macro indicators")
with card4:
    metric_card("Pipeline flows", f"{len(pipeline_rows)}", "Tracked data movements")

st.markdown('<div class="landing-h2">How it is organised</div>', unsafe_allow_html=True)
left, right = st.columns([1, 1], vertical_alignment="top")
with left:
    section_heading(
        "Three surfaces, one project",
        "FinLens is split into three views so each audience gets what it needs: the banking "
        "story for business readers, the build for data engineers, and the model for ML "
        "reviewers. Data flows from public sources, lands as raw artifacts, is normalised "
        "into canonical tables, and only dashboard-ready marts reach the surfaces.",
    )
    styled_table(_surface_summary())
with right:
    section_heading(
        "What is live right now",
        "These surfaces show live public data and runtime status. Where a source is not "
        "wired up yet, the UI labels it plainly instead of guessing.",
    )
    styled_table(_data_summary())

chart_note(
    "Use notice",
    "FinLens is a personal portfolio project using public data sources. It is not financial "
    "advice or a substitute for official U.S. government / regulator sources.",
)


from streamlit_app.lib.page_shell import page_footer  # noqa: E402

page_footer()
