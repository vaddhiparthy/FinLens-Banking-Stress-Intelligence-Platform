# ruff: noqa: E402

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx

PROJECT_ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").exists()
)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from finlens.config import get_settings
from finlens.warehouse import stress_pulse_source_mode
from streamlit_app.lib.data import load_stress_pulse
from streamlit_app.lib.page_shell import BUSINESS_PAGE, page_intro, status_ribbon, top_navigation
from streamlit_app.lib.telemetry import record_page_view
from streamlit_app.lib.theme import app_css, ensure_theme_state, get_theme_mode
from streamlit_app.lib.ui_components import (
    empty_state,
    inject_styles,
    metric_card,
    section_heading,
    stack_badges,
)


def add_recession_bands(figure: go.Figure) -> None:
    bands = [("2020Q1", "2020Q3"), ("2023Q1", "2023Q2")]
    for start, end in bands:
        figure.add_vrect(
            x0=start,
            x1=end,
            fillcolor="rgba(191, 109, 71, 0.08)",
            line_width=0,
            layer="below",
        )


def earnings_chart(frame: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    figure.add_bar(x=frame["quarter"], y=frame["net_income"], name="Net income ($B)")
    figure.add_scatter(
        x=frame["quarter"],
        y=frame["roa"],
        name="ROA (%)",
        mode="lines+markers",
        yaxis="y2",
    )
    figure.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        yaxis_title="Net income ($B)",
        yaxis2=dict(title="ROA (%)", overlaying="y", side="right"),
        legend=dict(orientation="h"),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
    )
    add_recession_bands(figure)
    return figure


def funding_chart(frame: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    figure.add_scatter(x=frame["quarter"], y=frame["asset_yield"], name="Yield on earning assets")
    figure.add_scatter(x=frame["quarter"], y=frame["funding_cost"], name="Cost of funds")
    figure.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h"),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
    )
    add_recession_bands(figure)
    return figure


def asset_quality_chart(frame: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    figure.add_scatter(x=frame["quarter"], y=frame["noncurrent_rate"], name="Noncurrent loan rate")
    figure.add_scatter(
        x=frame["quarter"],
        y=frame["nco_rate"],
        name="Net charge-off rate",
        yaxis="y2",
    )
    figure.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        yaxis_title="Noncurrent (%)",
        yaxis2=dict(title="NCO (%)", overlaying="y", side="right"),
        legend=dict(orientation="h"),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
    )
    add_recession_bands(figure)
    return figure


def unrealized_losses_chart(frame: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    figure.add_scatter(
        x=frame["quarter"],
        y=frame["afs_losses"],
        stackgroup="losses",
        name="AFS unrealized gains/losses",
    )
    figure.add_scatter(
        x=frame["quarter"],
        y=frame["htm_losses"],
        stackgroup="losses",
        name="HTM unrealized gains/losses",
    )
    figure.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h"),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        annotations=[
            dict(
                x="2023Q1",
                y=-180,
                text="March 2023",
                showarrow=True,
                arrowhead=2,
            )
        ],
    )
    add_recession_bands(figure)
    return figure


@st.dialog("Welcome to FinLens", width="large")
def show_welcome_dialog() -> None:
    st.markdown(
        """
        <div class="welcome-summary">
            FinLens is a banking stress intelligence platform architected end-to-end by
            Sri Surya S. Vaddhiparthy. It demonstrates how stable public banking and macroeconomic
            sources can be ingested, normalized, reconciled, and served through durable analytical
            surfaces.
        </div>
        <div class="welcome-summary" style="margin-top:.55rem;">
            Continuing to use this project means you understand it is an educational analytics
            system, not supervisory advice or a prediction of any bank's success or failure.
            For authoritative information, rely on official U.S. government sources.
        </div>
        """,
        unsafe_allow_html=True,
    )
    stack_badges(["FDIC BankFind", "FDIC QBP", "FRED", "NIC", "Bronze / Silver / Gold"])
    st.markdown('<div class="welcome-grid">', unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        st.markdown(
            """
            <div class="welcome-card">
                <div class="welcome-kicker">Technical Surface</div>
                <div class="welcome-title">Open the control room</div>
                <div class="welcome-copy">
                    Inspect freshness, reconciliation, lineage, and the operating signals that
                    make the platform trustworthy.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Open", key="welcome_technical", use_container_width=True):
            st.session_state["welcome_dismissed"] = True
            st.switch_page("pages/4_Under_The_Hood.py")
    with right:
        st.markdown(
            """
            <div class="welcome-card">
                <div class="welcome-kicker">Business Surface</div>
                <div class="welcome-title">Open stress pulse</div>
                <div class="welcome-copy">
                    Read the industry-aggregate banking stress view built from resilient public
                    data contracts and dashboard-ready gold models.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Open", key="welcome_business", use_container_width=True):
            st.session_state["welcome_dismissed"] = True
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    if st.button("Close", key="welcome_close"):
        st.session_state["welcome_dismissed"] = True
        st.rerun()


settings = get_settings()
st.set_page_config(
    page_title=settings.streamlit_app_title,
    layout="wide",
    initial_sidebar_state="collapsed",
)
ensure_theme_state()
inject_styles(app_css(get_theme_mode(), sidebar_open=False))

if "welcome_dismissed" not in st.session_state:
    st.session_state["welcome_dismissed"] = False
if "welcome_shown_once" not in st.session_state:
    st.session_state["welcome_shown_once"] = False
if get_script_run_ctx() is not None and not st.session_state["welcome_shown_once"]:
    st.session_state["welcome_shown_once"] = True
    show_welcome_dialog()

frame = load_stress_pulse()
stress_pulse_mode = stress_pulse_source_mode()

top_navigation("overview", BUSINESS_PAGE)
record_page_view("stress_pulse", BUSINESS_PAGE)
status_ribbon("Industry aggregate view")
page_intro(
    "Business Surface",
    "Stress Pulse",
    "A low-risk, durable industry health surface built around stable aggregate banking signals. "
    "This page stays focused on what can refresh reliably over time without brittle joins or "
    "high-maintenance source logic.",
)

if frame.empty:
    empty_state(
        "Stress Pulse is waiting for a compatible FDIC QBP aggregate feed. "
        "No synthetic aggregate values are shown in production mode."
    )
    st.stop()

latest = frame.iloc[-1]
prev = frame.iloc[-2]

card1, card2, card3, card4 = st.columns(4)
with card1:
    metric_card(
        "Aggregate net income",
        f"${latest['net_income']:.0f}B",
        f"{latest['quarter']} · QoQ {latest['net_income'] - prev['net_income']:+.0f}B",
    )
with card2:
    metric_card(
        "Industry ROA",
        f"{latest['roa']:.2f}%",
        "Live aggregate feed" if stress_pulse_mode == "live" else "Aggregate feed pending",
    )
with card3:
    metric_card(
        "Industry NIM",
        f"{latest['nim']:.2f}%",
        f"QoQ {latest['nim'] - prev['nim']:+.2f} pts",
    )
with card4:
    metric_card(
        "Problem bank count",
        f"{int(latest['problem_banks'])}",
        f"QoQ {int(latest['problem_banks'] - prev['problem_banks']):+d}",
    )

section_heading(
    "Earnings And Funding",
    "This top layer mirrors the language of industry aggregate banking reporting: earnings, "
    "profitability, and the spread between asset yield and funding cost.",
)
left, right = st.columns(2)
with left:
    st.plotly_chart(earnings_chart(frame), width="stretch")
with right:
    st.plotly_chart(funding_chart(frame), width="stretch")

section_heading(
    "Asset Quality",
    "Charge-offs and noncurrent loan pressure belong together because they show both pipeline "
    "stress and realized deterioration.",
)
st.plotly_chart(asset_quality_chart(frame), width="stretch")

section_heading(
    "Unrealized Losses",
    "The March 2023 regional banking crisis made this one of the most recognizable stress charts "
    "in the banking system. It stays here as a durable aggregate view for the final source feed.",
)
st.plotly_chart(unrealized_losses_chart(frame), width="stretch")
