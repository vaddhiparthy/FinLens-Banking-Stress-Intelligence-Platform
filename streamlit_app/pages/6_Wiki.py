# ruff: noqa: E402,E501

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").exists()
)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from streamlit_app.lib.page_shell import home_navigation
from streamlit_app.lib.telemetry import record_page_view
from streamlit_app.lib.theme import app_css, ensure_theme_state, get_theme_mode
from streamlit_app.lib.ui_components import inject_styles, styled_table
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

home_navigation()

st.markdown(
    """
    <div class="wiki-head">
        <div class="wiki-head-title">Wiki</div>
        <div class="wiki-head-sub">How I think about the banking concepts, the data
        architecture, and the operating evidence behind FinLens. One page, jump-linked,
        no reloads.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

query = st.text_input(
    "Search Wiki",
    placeholder="Search source contracts, warehouse layers, Airflow, dbt, business concepts...",
    key="wiki_search",
    label_visibility="collapsed",
).strip()

matches = _matching_articles(query)
tree = _tree(matches)

left, center = st.columns([0.9, 3.1], gap="large")
with left:
    toc = ['<nav class="wiki-toc"><div class="wiki-toc-title">Contents</div>']
    for cluster, branches in tree.items():
        toc.append(f'<div class="wiki-toc-cluster">{cluster}</div>')
        for branch, titles in branches.items():
            toc.append(f'<div class="wiki-toc-branch">{branch}</div>')
            for title in titles:
                toc.append(f'<a class="wiki-toc-link" href="#{_slug(title)}">{title}</a>')
    toc.append("</nav>")
    st.markdown("\n".join(toc), unsafe_allow_html=True)

with center:
    if not matches:
        st.info("No articles match your search.")
    for title in matches:
        article = ARTICLES[title]
        crumb = article["cluster"]
        if article["branch"] and article["branch"] != article["cluster"]:
            crumb = f'{article["cluster"]} / {article["branch"]}'
        st.markdown(
            f'<div id="{_slug(title)}" class="wiki-art-title">{title}</div>'
            f'<div class="wiki-art-meta">{crumb} · {article["summary"]}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(article["body"])
        if title == "Product Operating Model":
            styled_table(_article_index())
        elif title == "Source Contracts":
            styled_table(_source_contract_table())
        elif title == "Warehouse Layers":
            styled_table(_warehouse_layer_table())
        st.markdown('<div class="wiki-art-divider"></div>', unsafe_allow_html=True)


from streamlit_app.lib.page_shell import page_footer  # noqa: E402

page_footer()
