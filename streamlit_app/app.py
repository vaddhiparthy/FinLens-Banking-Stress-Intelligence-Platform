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

from streamlit_app.lib.page_shell import home_navigation, page_footer
from streamlit_app.lib.telemetry import record_page_view
from streamlit_app.lib.theme import app_css, ensure_theme_state, get_theme_mode
from streamlit_app.lib.ui_components import inject_styles

st.set_page_config(
    page_title="FinLens: Banking Stress Intelligence",
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
        background: #bf6d47 !important; border: 1px solid #bf6d47 !important;
        border-radius: 11px !important; box-shadow: 0 8px 20px rgba(15,23,42,.16) !important;
        margin-top: .2rem;
    }
    div[role="dialog"] div[data-testid="stButton"] > button:hover {
        background: #a85b38 !important; border-color: #a85b38 !important;
    }
    div[role="dialog"] div[data-testid="stButton"] > button,
    div[role="dialog"] div[data-testid="stButton"] > button * {
        color: #fff !important; -webkit-text-fill-color: #fff !important; font-weight: 700 !important;
    }
    div[role="dialog"] div[data-testid="stButton"] > button * { background: transparent !important; }
    .gate-brand { font-weight: 800; letter-spacing: .02em; color: #bf6d47; font-size: .82rem;
        text-transform: uppercase; margin-bottom: .1rem; }

    /* Browse-the-project hub */
    .browse-head {
        text-align: center; font-family: "Inter", system-ui, sans-serif; font-weight: 800;
        font-size: 1.5rem; color: #1f2933; margin: 2rem 0 .2rem;
    }
    .browse-head-sub { text-align: center; color: #7f6b58; font-size: .85rem; margin-bottom: 1rem; }
    .st-key-browse_box { border: 1px solid #e4d7c6; border-radius: 18px; background: #fffaf3;
        padding: 1.2rem 1.4rem; box-shadow: 0 10px 30px rgba(15,23,42,.06); }
    .browse-col-h { font-size: .72rem; font-weight: 800; letter-spacing: .14em; text-transform: uppercase;
        color: #bf6d47; margin: .2rem 0 .7rem; }
    .browse-div { border-left: 1px solid #e4d7c6; height: 100%; min-height: 320px; margin: 0 auto; width: 1px; }
    .home-head { text-align: left; margin: .4rem 0 0; }
    .home-intro { text-align: left; color: #6a6b74; font-size: 1rem; line-height: 1.6;
        margin: .25rem 0 1.4rem; }
    /* Browse links: clean text + accent hover (no boxes); description lives in the button help tip */
    div[class*="st-key-nav_"] button {
        background: transparent !important; border: none !important; box-shadow: none !important;
        color: #1f2933 !important; font-weight: 700 !important; font-size: 1rem !important;
        text-align: left !important; justify-content: flex-start !important;
        padding: .3rem 0 !important; min-height: 0 !important;
    }
    /* keep the chevron and the label as one left-packed unit (Streamlit centers the inner flex) */
    div[class*="st-key-nav_"] button > div {
        justify-content: flex-start !important; width: auto !important; }
    div[class*="st-key-nav_"] button::before { content: "›  "; color: #bf6d47; font-weight: 800; }
    div[class*="st-key-nav_"] button:hover,
    div[class*="st-key-nav_"] button:hover * {
        color: #bf6d47 !important; -webkit-text-fill-color: #bf6d47 !important; }
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

# Title + intro: no boxes.
st.markdown(
    """
    <div class="home-head">
        <div class="landing-eyebrow">Surya Vaddhiparthy · M.S. Data Science</div>
        <div class="landing-h1">FinLens</div>
    </div>
    <p class="home-intro">
        FinLens turns free public banking data into an early-warning read on U.S. bank distress. It
        lands FDIC Call Reports, the failed-bank list, FRED macro series, and FFIEC institution data
        as immutable raw snapshots, runs them through a Bronze → Silver → Gold dbt pipeline on DuckDB
        (quality-gated by Great Expectations), and scores each bank's probability of financial distress
        within four quarters with a calibrated, monotone, 12-seed bagged LightGBM hazard model
        evaluated out-of-time, explained with SHAP, served via FastAPI, and queryable through a
        cited assistant.
    </p>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="browse-head">Browse the project</div>'
            '<div class="browse-head-sub">Interactive surfaces on the left · the technical build on '
            'the right</div>', unsafe_allow_html=True)

_LEFT = [
    ("AI Inference", "Chat with the cited model and watch a bank's live read appear.",
     "pages/9_AI_Inference.py", None),
    ("Machine Learning", "Score any bank, see what actually happened, and run what-ifs.",
     "pages/3_Early_Warning.py", None),
    ("Business Dashboard", "Earnings, asset quality, the 2023 shock, failures, macro: at a glance.",
     "pages/10_Business_Dashboard.py", None),
    ("Wikipedia", "The encyclopedia: domain, architecture, data engineering, and the model.",
     "pages/6_Wiki.py", None),
]
_RIGHT = [
    ("Technical Dashboard", "Model performance, calibration, drivers, and live pipeline status.",
     "pages/11_Technical_Dashboard.py", None),
    ("AI Pipeline", "The AI Engineering surface: training, evaluation, SHAP, drift, governance.",
     "pages/7_AI_Engineering.py", None),
    ("Data Engineering Pipeline", "The DE surface: source contracts, warehouse, quality, operations.",
     "pages/4_Data_Engineering.py", None),
    ("Architecture Diagram", "The whole platform end to end, every component, hover for detail.",
     "pages/6_Wiki.py", "system-architecture"),
]


def _nav(items: list, side: str) -> None:
    for title, desc, target, article in items:
        key = f"nav_{side}_{title.lower().replace(' ', '_')}"
        # clean text link; the one-line description is the hover help (no boxes)
        if st.button(title, key=key, help=desc, use_container_width=True):
            if article:
                st.session_state["wiki_article"] = article
            elif target.endswith("4_Data_Engineering.py"):
                st.session_state["technical_section"] = "pipeline"
            st.switch_page(target)


with st.container(key="browse_box"):
    col_l, col_div, col_r = st.columns([1, 0.05, 1])
    with col_l:
        st.markdown('<div class="browse-col-h">Interactive</div>', unsafe_allow_html=True)
        _nav(_LEFT, "l")
    with col_div:
        st.markdown('<div class="browse-div"></div>', unsafe_allow_html=True)
    with col_r:
        st.markdown('<div class="browse-col-h">Technical</div>', unsafe_allow_html=True)
        _nav(_RIGHT, "r")

page_footer()
