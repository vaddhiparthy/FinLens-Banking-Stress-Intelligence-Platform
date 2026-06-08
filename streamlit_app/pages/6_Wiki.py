# ruff: noqa: E402

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").exists()
)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from streamlit_app.lib import wiki_app
from streamlit_app.lib.page_shell import home_navigation, page_footer
from streamlit_app.lib.telemetry import record_page_view
from streamlit_app.lib.theme import app_css, ensure_theme_state, get_theme_mode
from streamlit_app.lib.ui_components import inject_styles

st.set_page_config(page_title="FinLens | Wiki", layout="wide", initial_sidebar_state="collapsed")
ensure_theme_state()
inject_styles(app_css(get_theme_mode(), sidebar_open=False))
record_page_view("wiki", "shared")
home_navigation()

# The whole wiki is a fast client-side SPA (instant nav, search, in-app wikilinks, and the
# architecture diagram rendered in-place with viz.js + pan/zoom). A deep-link ?article=<slug> or a
# hamburger hand-off opens that article directly.
slug = st.query_params.get("article", "") or st.session_state.pop("wiki_article", "")
wiki_app.render_wiki_app(slug or None)

page_footer()
