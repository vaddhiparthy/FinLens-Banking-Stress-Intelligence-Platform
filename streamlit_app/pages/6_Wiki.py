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

from streamlit_app.lib.architecture_docs import render_architecture_decisions
from streamlit_app.lib.page_shell import BUSINESS_PAGE, page_intro, status_ribbon, top_navigation
from streamlit_app.lib.telemetry import record_page_view
from streamlit_app.lib.theme import app_css, ensure_theme_state, get_theme_mode
from streamlit_app.lib.ui_components import chart_note, inject_styles, section_heading, styled_table

ARTICLES = {
    "About Me": {
        "group": "Project Orientation",
        "summary": "Author, credential, and project intent.",
        "body": """
FinLens was authored and engineered by **Sri Surya S. Vaddhiparthy, M.S. (Data Science)** as a public-data banking intelligence and data engineering portfolio system.

The project demonstrates how a banking-domain analytical product can be built from public feeds while preserving a traceable data path: source contract, raw landing, canonical shaping, governed marts, quality checks, serving layer, and operational monitoring.

Portfolio: [surya.vaddhiparthy.com](https://surya.vaddhiparthy.com)
""",
    },
    "Platform Overview": {
        "group": "Project Orientation",
        "summary": "What the product does and how the surfaces are organized.",
        "body": """
FinLens is organized as two complementary surfaces. The **Business Surface** explains banking stress through industry health, failure history, and macro context. The **Technical Surface** shows how the data is acquired, landed, modeled, validated, and served.

The product is intentionally not a bank-failure prediction tool. It is a governed analytical system that turns public banking and macroeconomic data into readable decision context and traceable engineering artifacts.
""",
    },
    "Business Concepts": {
        "group": "Business Knowledge",
        "summary": "Plain-English definitions for the banking analysis.",
        "body": """
The business layer focuses on a few durable questions: whether the industry is profitable, where historical failures clustered, what macro conditions existed around stress periods, and whether the displayed numbers can be traced back to stable public sources.

Key concepts include aggregate net income, return on assets, net interest margin, noncurrent loan rate, failure count, failure year, acquirer, yield-curve spread, unemployment, CPI, and GDP. These measures are presented as context, not supervisory ratings or investment advice.
""",
    },
    "Source Contracts": {
        "group": "Data Engineering",
        "summary": "Public feeds and the role each source plays.",
        "body": """
The active source design centers on public, repeatable feeds: FDIC failed-bank records, FDIC/QBP-style aggregate banking data, FRED macroeconomic series, and current institution metadata. Each source is treated as a contract with a cadence, landing pattern, and Gold-layer usage.

The platform separates source readiness from runtime evidence. A source can be configured, actively landed, or deferred. The technical surface should report the current runtime state from artifacts and pipeline status rather than stale configuration flags.
""",
    },
    "Warehouse Layers": {
        "group": "Data Engineering",
        "summary": "Bronze, Silver, Intermediate, and Gold boundaries.",
        "body": """
The platform follows a layered warehouse pattern. **Bronze** preserves source-shaped raw artifacts. **Silver** standardizes names, dates, identifiers, and types. **Intermediate** is reserved for reusable joins and business shaping. **Gold** is the dashboard contract consumed by Streamlit.

Dashboards should bind to Gold tables only. This keeps visualization code stable even when source fields or ingestion formats change.
""",
    },
    "Orchestration And Modeling": {
        "group": "Data Engineering",
        "summary": "How Airflow, dbt, Snowflake, DuckDB, and Streamlit fit together.",
        "body": """
Airflow owns scheduling, dependencies, retry behavior, and run visibility. Python connectors perform source acquisition. dbt owns SQL modeling, semantic shaping, and data tests. Snowflake is the enterprise warehouse target. DuckDB keeps the system testable and demonstrable at low cost. Streamlit serves the analytical surfaces.

The intended operating path is source acquisition, raw landing, model build, quality checks, mart publication, and dashboard serving.
""",
    },
    "Data Quality": {
        "group": "Data Engineering",
        "summary": "Controls that make the numbers credible.",
        "body": """
The quality posture is based on row counts, source freshness, schema-aware contracts, dbt test artifacts, reconciliation checks, and read-only table previews. These controls are designed to show whether the pipeline is current, complete, and internally consistent.

Quality language should be precise: a table is passed, blocked, missing, or deferred. It should not imply validation that has not actually run.
""",
    },
    "Deployment And Operations": {
        "group": "Operations",
        "summary": "Serving model, health checks, and production runtime.",
        "body": """
The production deployment uses Docker Compose behind Caddy and Cloudflare. Streamlit serves the user-facing application, FastAPI exposes machine-readable health status, and Uptime Kuma can monitor the public health endpoint.

The preferred public route is a subdomain because Streamlit handles root-path deployment more reliably than path-prefix deployment. A path route such as `/portfolio/FinLens` is possible, but it requires reverse-proxy and Streamlit base-path testing.
""",
    },
}


def _article_index() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Section": article["group"], "Article": title, "Summary": article["summary"]}
            for title, article in ARTICLES.items()
        ]
    )


def _matching_articles(query: str) -> list[str]:
    if not query:
        return list(ARTICLES)
    text = query.lower()
    matches = []
    for title, article in ARTICLES.items():
        haystack = " ".join([title, article["group"], article["summary"], article["body"]]).lower()
        if text in haystack:
            matches.append(title)
    return matches or list(ARTICLES)


st.set_page_config(page_title="FinLens | Wiki", layout="wide", initial_sidebar_state="collapsed")
ensure_theme_state()
inject_styles(app_css(get_theme_mode(), sidebar_open=False))
top_navigation("wiki", st.session_state.get("surface_mode", BUSINESS_PAGE))
record_page_view("wiki", "shared")
status_ribbon("Shared knowledge bank")
page_intro(
    "FinLens Wiki",
    "Knowledge Bank",
    "A shared reference surface for the business meaning, data engineering design, source contracts, "
    "quality posture, and operational model behind FinLens.",
)

query = st.text_input(
    "Search Wiki",
    placeholder="Search source contracts, warehouse layers, Airflow, dbt, business concepts...",
    key="wiki_search",
).strip()

left, center = st.columns([0.95, 3.05], gap="large")
matches = _matching_articles(query)
if st.session_state.get("wiki_article") not in matches:
    st.session_state["wiki_article"] = matches[0]
with left:
    st.markdown("#### Contents")
    selected = st.radio(
        "Wiki articles",
        matches,
        label_visibility="collapsed",
        key="wiki_article",
    )
    st.markdown("---")
    st.page_link("app.py", label="Main Landing Page", icon=":material/home:")
    st.page_link("pages/0_Stress_Pulse.py", label="Business Surface", icon=":material/space_dashboard:")
    st.page_link("pages/4_Under_The_Hood.py", label="Technical Surface", icon=":material/account_tree:")

with center:
    article = ARTICLES[selected]
    section_heading(selected, f"{article['group']} · {article['summary']}")
    st.markdown(article["body"])
    chart_note(
        "Reference posture",
        "FinLens documentation describes the implemented platform and its intended operating model. "
        "Credentials, secrets, and private infrastructure details are intentionally excluded.",
    )

    if selected == "Platform Overview":
        section_heading("Article Index", "Current Wiki articles and where they fit.")
        styled_table(_article_index())
    if selected == "Source Contracts":
        styled_table(
            pd.DataFrame(
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
        )
    if selected == "Warehouse Layers":
        styled_table(
            pd.DataFrame(
                [
                    {"Layer": "Bronze", "Purpose": "Source fidelity", "Consumer": "Normalization jobs"},
                    {"Layer": "Silver", "Purpose": "Canonical shaping", "Consumer": "Intermediate models"},
                    {"Layer": "Intermediate", "Purpose": "Reusable business logic", "Consumer": "Gold marts"},
                    {"Layer": "Gold", "Purpose": "Dashboard contract", "Consumer": "Streamlit / FastAPI"},
                ]
            )
        )

    with st.expander("Full Architecture Handbook", expanded=False):
        render_architecture_decisions()
