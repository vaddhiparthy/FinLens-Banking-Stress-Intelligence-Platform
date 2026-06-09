# ruff: noqa: E402,E501
"""Immersive full-screen architecture diagram.

Opens edge-to-edge with no chrome: the whole system diagram fills the viewport, zoom/pan enabled, a
floating close (x) returns to the home landing, and a single pinned link opens the architecture wiki.
"""

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

from streamlit.components.v1 import html as _html

from streamlit_app.lib.telemetry import record_page_view
from streamlit_app.lib.theme import app_css, ensure_theme_state, get_theme_mode
from streamlit_app.lib.ui_components import inject_styles
from streamlit_app.lib.wiki_architecture import _PANZOOM_JS, ARCHITECTURE_DOT

st.set_page_config(page_title="FinLens | Architecture", layout="wide",
                   initial_sidebar_state="collapsed")
ensure_theme_state()
inject_styles(app_css(get_theme_mode(), sidebar_open=False))
record_page_view("architecture_immersive", "technical")

# Full-bleed immersion: strip all Streamlit chrome and padding, let the diagram own the viewport.
st.markdown(
    """
    <style>
    [data-testid="stHeader"], [data-testid="stToolbar"], header {display:none !important;}
    html, body {overflow:hidden !important;}
    .block-container, [data-testid="stMainBlockContainer"] {
        padding:0 !important; max-width:100% !important;}
    [data-testid="stGraphVizChart"], .stGraphVizChart {
        height:100vh !important; width:100% !important; border:none !important; border-radius:0 !important;
        background:#fffaf3 !important; box-shadow:none !important; overflow:hidden;}
    [data-testid="stGraphVizChart"] > svg, .stGraphVizChart > svg {
        width:100% !important; height:100% !important;}
    .svg-pan-zoom-control-background {fill:#fffaf3; opacity:.85;}
    .svg-pan-zoom-control-element {fill:#bf6d47;}
    /* floating controls layered over the diagram */
    .arch-close {position:fixed; top:16px; right:18px; z-index:99999; width:44px; height:44px;
        border-radius:50%; background:#fffaf3; border:1px solid #e4d7c6; color:#1f2933 !important;
        font-size:1.6rem; font-weight:600; line-height:42px; text-align:center;
        text-decoration:none !important; box-shadow:0 6px 18px rgba(15,23,42,.14);}
    .arch-close:hover {border-color:#bf6d47; color:#bf6d47 !important;}
    .arch-wiki {position:fixed; bottom:20px; left:50%; transform:translateX(-50%); z-index:99999;
        background:#bf6d47; color:#fff7ef !important; font-weight:700; font-size:.88rem;
        padding:.6rem 1.25rem; border-radius:999px; text-decoration:none !important;
        box-shadow:0 8px 22px rgba(191,109,71,.32);}
    .arch-wiki:hover {background:#a8501f;}
    </style>
    <a class="arch-close" href="." target="_self" title="Close">&times;</a>
    <a class="arch-wiki" href="Wiki?article=system-architecture" target="_self">Open the architecture wiki &rarr;</a>
    """,
    unsafe_allow_html=True,
)

st.graphviz_chart(ARCHITECTURE_DOT, use_container_width=True)
_html(_PANZOOM_JS, height=0)
