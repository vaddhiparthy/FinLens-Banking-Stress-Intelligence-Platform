# ruff: noqa: E402,E501

import sys
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import streamlit as st

PROJECT_ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").exists()
)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from streamlit_app.lib.telemetry import record_page_view
from streamlit_app.lib.theme import app_css, ensure_theme_state, get_theme_mode
from streamlit_app.lib.ui_components import chart_note, inject_styles, section_heading, styled_table
from streamlit_app.lib.wiki_content import ARTICLES


def _article_index() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Cluster": article["cluster"],
                "Branch": article["branch"],
                "Article": title,
                "Summary": article["summary"],
            }
            for title, article in ARTICLES.items()
        ]
    )


def _matching_articles(query: str) -> list[str]:
    if not query:
        return list(ARTICLES)
    text = query.lower()
    matches = []
    for title, article in ARTICLES.items():
        haystack = " ".join(
            [title, article["cluster"], article["branch"], article["summary"], article["body"]]
        ).lower()
        if text in haystack:
            matches.append(title)
    return matches or list(ARTICLES)


def _tree(matches: list[str]) -> dict[str, dict[str, list[str]]]:
    tree: dict[str, dict[str, list[str]]] = {}
    for title in matches:
        article = ARTICLES[title]
        tree.setdefault(article["cluster"], {}).setdefault(article["branch"], []).append(title)
    return tree


def _slug(title: str) -> str:
    return title.lower().replace(" ", "-").replace("/", "-")


SLUG_TO_TITLE = {_slug(title): title for title in ARTICLES}


def _source_contract_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Source": "FDIC failed-bank records",
                "Cadence": "Manual / periodic",
                "Landing": "Bronze raw artifact",
                "Gold usage": "Failure timeline, inventory, filters",
            },
            {
                "Source": "FRED macro series",
                "Cadence": "Daily",
                "Landing": "Bronze observation panel",
                "Gold usage": "Macro context and indicator detail",
            },
            {
                "Source": "FDIC/QBP aggregate banking data",
                "Cadence": "Quarterly",
                "Landing": "Bronze aggregate artifact",
                "Gold usage": "Stress Pulse industry metrics",
            },
            {
                "Source": "Current institution metadata",
                "Cadence": "Quarterly / periodic",
                "Landing": "Bronze metadata artifact",
                "Gold usage": "Institution and parent context",
            },
        ]
    )


def _warehouse_layer_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Layer": "Bronze", "Purpose": "Source fidelity", "Consumer": "Normalization jobs"},
            {"Layer": "Silver", "Purpose": "Canonical shaping", "Consumer": "Intermediate models"},
            {"Layer": "Intermediate", "Purpose": "Reusable business logic", "Consumer": "Gold marts"},
            {"Layer": "Gold", "Purpose": "Dashboard contract", "Consumer": "Streamlit / FastAPI"},
        ]
    )


st.set_page_config(page_title="FinLens | Wiki", layout="wide", initial_sidebar_state="collapsed")
ensure_theme_state()
inject_styles(app_css(get_theme_mode(), sidebar_open=False))
record_page_view("wiki", "shared")

st.markdown(
    """
    <div class="edge-brand">
        <span class="edge-brand-copy">
            <span class="edge-title">FinLens</span>
            <span class="edge-subtitle">Banking</span>
            <span class="edge-subtitle">Stress Intelligence</span>
        </span>
    </div>
    <a class="edge-credit" href="https://surya.vaddhiparthy.com" target="_blank">
        Built by Sri Surya S. Vaddhiparthy
    </a>
    """,
    unsafe_allow_html=True,
)

header_left, header_right = st.columns([1.08, 2.92], vertical_alignment="center")
with header_left:
    st.markdown(
        """
        <div class="wiki-brand-card">
            <div class="wiki-brand-kicker">FinLens Wiki</div>
            <div class="wiki-brand-title">Knowledge Bank</div>
            <div class="wiki-brand-copy">Business meaning, data architecture, and operating evidence.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with header_right:
    query = st.text_input(
        "Search Wiki",
        placeholder="Search source contracts, warehouse layers, Airflow, dbt, business concepts...",
        key="wiki_search",
    ).strip()

matches = _matching_articles(query)
requested_article = SLUG_TO_TITLE.get(st.query_params.get("article", ""))
if requested_article in matches:
    st.session_state["wiki_article"] = requested_article
elif st.session_state.get("wiki_article") not in matches:
    st.session_state["wiki_article"] = matches[0]

left, center = st.columns([0.92, 3.08], gap="large")
with left:
    st.markdown('<div class="wiki-nav-title">Navigation</div>', unsafe_allow_html=True)
    st.page_link("app.py", label="Main Landing Page", icon=":material/home:")
    st.page_link("pages/0_Stress_Pulse.py", label="Business Surface", icon=":material/space_dashboard:")
    st.page_link("pages/4_Under_The_Hood.py", label="Technical Surface", icon=":material/account_tree:")
    st.markdown('<div class="wiki-nav-title wiki-nav-spaced">Contents</div>', unsafe_allow_html=True)
    tree_html = ['<div class="wiki-tree">']
    for cluster, branches in _tree(matches).items():
        tree_html.append(f'<div class="wiki-tree-cluster">{cluster}</div>')
        for branch, titles in branches.items():
            tree_html.append(f'<div class="wiki-tree-branch">{branch}</div>')
            for title in titles:
                active_class = " active" if title == st.session_state.get("wiki_article") else ""
                href = f"?article={quote(_slug(title))}"
                tree_html.append(
                    f'<a class="wiki-tree-link{active_class}" href="{href}" target="_self">'
                    f"{title}</a>"
                )
    tree_html.append("</div>")
    st.markdown("\n".join(tree_html), unsafe_allow_html=True)

selected = st.session_state["wiki_article"]
with center:
    article = ARTICLES[selected]
    section_heading(selected, f"{article['cluster']} / {article['branch']} · {article['summary']}")
    st.markdown(article["body"])
    chart_note(
        "Reference posture",
        "FinLens documentation describes the implemented platform and intended operating model. "
        "Credentials, secrets, and private infrastructure details are intentionally excluded.",
    )

    if selected == "Product Operating Model":
        section_heading("Article Index", "Current Wiki articles grouped by cluster and branch.")
        styled_table(_article_index())
    if selected == "Source Contracts":
        styled_table(_source_contract_table())
    if selected == "Warehouse Layers":
        styled_table(_warehouse_layer_table())
