# ruff: noqa: E402,E501

import re
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").exists()
)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from streamlit_app.lib import wiki_app
from streamlit_app.lib import wiki_architecture as wa
from streamlit_app.lib import wiki_structure as ws
from streamlit_app.lib.page_shell import home_navigation, page_footer
from streamlit_app.lib.telemetry import record_page_view
from streamlit_app.lib.theme import app_css, ensure_theme_state, get_theme_mode
from streamlit_app.lib.ui_components import inject_styles

st.set_page_config(page_title="FinLens | Wiki", layout="wide", initial_sidebar_state="collapsed")
ensure_theme_state()
inject_styles(app_css(get_theme_mode(), sidebar_open=False))
record_page_view("wiki", "shared")
home_navigation()


_LINK = re.compile(r"\[\[([^\]]+)\]\]")


def _wikilinks(body: str) -> str:
    """Convert [[Article Title]] cross-links into clickable article links."""
    def repl(m: re.Match) -> str:
        title = m.group(1).strip()
        if title in ws.ARTICLES:
            return f'<a target="_self" href="?article={ws.slug(title)}">{title}</a>'
        return title
    return _LINK.sub(repl, body)


# ---- routing ----
# Browsing is a fast client-side SPA (instant, no rerun per article). The single article with a
# live Graphviz diagram (System Architecture) keeps its Streamlit route so the interactive
# pan/zoom diagram still renders; the SPA links out to it.
slug = st.query_params.get("article", "") or st.session_state.pop("wiki_article", "")
_ARCH = ws.slug("System Architecture")

if slug == _ARCH:
    a = ws.article("System Architecture")
    st.markdown('<a class="wiki-crumb-home" target="_self" href="?article=">‹ Back to the wiki</a>',
                unsafe_allow_html=True)
    st.markdown(
        f'<div class="wiki-art-title">System Architecture</div>'
        f'<div class="wiki-art-lead">{a.get("summary", "")}</div>',
        unsafe_allow_html=True,
    )
    wa.render_architecture()
    with st.container(key="wiki_article_body"):
        st.markdown(_wikilinks(a["body"]), unsafe_allow_html=True)
    prev, nxt = ws.neighbours("System Architecture")
    nav_html = '<div class="wiki-art-nav">'
    if prev:
        nav_html += f'<a class="wiki-prev" target="_self" href="?article={ws.slug(prev)}">‹ {prev}</a>'
    if nxt:
        nav_html += f'<a class="wiki-next" target="_self" href="?article={ws.slug(nxt)}">{nxt} ›</a>'
    nav_html += "</div>"
    st.markdown(nav_html, unsafe_allow_html=True)
else:
    wiki_app.render_wiki_app(slug or None)

page_footer()
