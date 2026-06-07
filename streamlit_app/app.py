# ruff: noqa: E402

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").exists()
)
for sub in ("", "src", "ml"):
    p = str(PROJECT_ROOT / sub) if sub else str(PROJECT_ROOT)
    if p not in sys.path:
        sys.path.insert(0, p)

from streamlit_app.lib import command_center as cc
from streamlit_app.lib.page_shell import home_navigation, page_footer
from streamlit_app.lib.telemetry import record_page_view
from streamlit_app.lib.theme import app_css, ensure_theme_state, get_theme_mode
from streamlit_app.lib.ui_components import inject_styles

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
    div[role="dialog"] { border-radius: 18px !important; }
    div[role="dialog"] button[aria-label="Close"] { display: none !important; }
    div[role="dialog"] [data-testid="stVerticalBlock"] { gap: .6rem !important; }
    div[role="dialog"] div[data-testid="stButton"] > button {
        background: #bf6d47 !important;
        border: 1px solid #bf6d47 !important;
        border-radius: 11px !important;
        box-shadow: 0 8px 20px rgba(15, 23, 42, .16) !important;
        margin-top: .2rem;
    }
    div[role="dialog"] div[data-testid="stButton"] > button:hover {
        background: #a85b38 !important; border-color: #a85b38 !important;
    }
    div[role="dialog"] div[data-testid="stButton"] > button,
    div[role="dialog"] div[data-testid="stButton"] > button * {
        color: #ffffff !important; -webkit-text-fill-color: #ffffff !important;
        font-weight: 700 !important;
    }
    div[role="dialog"] div[data-testid="stButton"] > button * { background: transparent !important; }
    .gate-brand {
        font-weight: 800; letter-spacing: .02em; color: #bf6d47;
        font-size: .82rem; text-transform: uppercase; margin-bottom: .1rem;
    }
    /* Command center */
    .cc-band-title {
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        font-weight: 800; font-size: 1.05rem; color: #1f2933;
        margin: .2rem 0 .9rem;
    }
    .cc-rule { height: 1px; background: #e4d7c6; margin: 1.4rem 0 1.1rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.dialog("Important Use Notice", width="small", dismissible=False)
def _legal_disclaimer() -> None:
    st.markdown('<div class="gate-brand">FinLens · Banking Stress Intelligence</div>',
                unsafe_allow_html=True)
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
    if st.button("I understand", key="accept_home_disclaimer", use_container_width=True,
                 type="primary"):
        st.session_state["home_disclaimer_accepted"] = True
        st.rerun()


if not st.session_state.get("home_disclaimer_accepted"):
    _legal_disclaimer()

home_navigation()

# Compact hero — the dense command center below is the focus.
st.markdown(
    """
    <div class="landing-hero">
        <div class="landing-eyebrow">Surya Vaddhiparthy · M.S. Data Science</div>
        <div class="landing-h1">Spotting financial stress<br>in U.S. banks</div>
        <p class="landing-sub">
            A calibrated machine-learning read on bank distress, on a full data-engineering
            pipeline over free public data. Live metrics, the riskiest banks right now, and a
            hands-on inference console — all in one place.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_overview, tab_inference = st.tabs(["⚡ Live Overview", "🔬 ML Inference"])
with tab_overview:
    cc.render_overview()
with tab_inference:
    cc.render_inference()

page_footer()
