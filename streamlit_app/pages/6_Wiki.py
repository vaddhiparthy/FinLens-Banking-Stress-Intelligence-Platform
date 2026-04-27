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

from streamlit_app.lib.architecture_docs import render_architecture_decisions
from streamlit_app.lib.telemetry import record_page_view
from streamlit_app.lib.theme import app_css, ensure_theme_state, get_theme_mode
from streamlit_app.lib.ui_components import chart_note, inject_styles, section_heading, styled_table

ARTICLES = {
    "About The Data Architect And Engineer": {
        "cluster": "Orientation",
        "branch": "Author",
        "summary": "Author, credential, and project intent.",
        "body": """
FinLens was authored and engineered by **Sri Surya S. Vaddhiparthy, M.S. (Data Science)** as a public-data banking intelligence and data engineering portfolio system.

The project demonstrates an end-to-end data product: public source acquisition, raw retention, warehouse-style modeling, analytical marts, data quality controls, technical observability, and a business-facing analytical surface.

Portfolio: [surya.vaddhiparthy.com](https://surya.vaddhiparthy.com)
""",
    },
    "Product Operating Model": {
        "cluster": "Orientation",
        "branch": "System Map",
        "summary": "How the product is organized for business and technical readers.",
        "body": """
FinLens is organized as two complementary surfaces. The **Business Surface** explains banking stress through industry health, failure history, and macro context. The **Technical Surface** shows how the data is acquired, landed, modeled, validated, and served.

The product is not a bank-failure prediction system and does not represent a regulator, bank, or investment advisor. It is a governed analytical system that converts public banking and macroeconomic feeds into readable decision context and traceable engineering artifacts.

The Wiki is the shared knowledge bank. It explains what the numbers mean, how the data moves, what each platform component contributes, and where the operating evidence lives.
""",
    },
    "Banking Stress Concepts": {
        "cluster": "Business Concepts",
        "branch": "Banking Interpretation",
        "summary": "Plain-English definitions behind the business charts.",
        "body": """
Banking stress is read through profitability, funding pressure, credit quality, failure history, and macro conditions. FinLens keeps those concepts separate so a user does not mistake a macro warning sign for a bank-specific supervisory conclusion.

**Aggregate net income** describes industry profit after expenses. **ROA** normalizes earnings by asset size. **NIM** shows the spread between asset income and funding cost. **Noncurrent loans** indicate serious delinquency or nonaccrual pressure. **Failure counts** show historical closures, not forward-looking predictions.

The business surface therefore answers practical questions: how healthy does the industry look at the aggregate level, where did failures cluster, what macro conditions surrounded historical stress, and which data points are source-backed.
""",
    },
    "Failure Forensics Concepts": {
        "cluster": "Business Concepts",
        "branch": "Failure Analysis",
        "summary": "How failed-bank records are converted into analysis.",
        "body": """
The FDIC failed-bank list is useful only after it is shaped into analytical fields: institution name, closing date, failure year, state, acquirer, and record-level identifiers where available.

FinLens turns that source list into a timeline, geography view, inventory table, and selected-bank readout. The analytical value comes from standardizing the event date, making year/state filters reliable, cleaning public text fields, and preserving acquirer context without presenting the result as a predictive model.
""",
    },
    "Macro Context Concepts": {
        "cluster": "Business Concepts",
        "branch": "Economic Context",
        "summary": "What macro indicators contribute and what they do not prove.",
        "body": """
FRED indicators provide economic context around banking stress: yield-curve spreads, unemployment, CPI, GDP, and housing-related series. These series differ by frequency, units, scale, and history length, so they should not be forced into one misleading combined axis.

FinLens presents macro indicators as context and lead-lag exploration. It does not claim that one indicator mechanically causes a bank failure. The value is disciplined framing: current value, history, trend shape, and relation to prior stress windows.
""",
    },
    "Architecture Desk": {
        "cluster": "Technical Concepts",
        "branch": "Architect Desk",
        "summary": "Architecture principles that govern the platform.",
        "body": """
The architecture is built around one rule: dashboards read governed Gold outputs, not raw source payloads. That separation lets the source layer change without forcing every chart to be rewritten.

The control path is source contract -> Bronze retention -> Silver normalization -> Intermediate shaping -> Gold mart -> dashboard/API serving. Each boundary has a clear responsibility and produces evidence that can be inspected from the technical surface.

The design favors low-cost operation, source traceability, and explainable controls over heavy enterprise infrastructure that would be expensive to maintain for a portfolio-scale deployment.
""",
    },
    "Data Plumbing": {
        "cluster": "Technical Concepts",
        "branch": "Data Plumbing",
        "summary": "How public records move into analytical tables.",
        "body": """
Data plumbing is the movement layer: connectors pull public source records, write source-shaped artifacts, load the warehouse runtime, and trigger model builds.

The intended resume stack is explicit: **AWS S3** for durable Bronze storage, **Airflow** for orchestration, **dbt** for SQL modeling and tests, **Snowflake** as the cloud warehouse target, **Terraform** for reproducible infrastructure, and **Streamlit/FastAPI** for serving. DuckDB remains the low-cost local/runtime fallback that keeps the product working without forcing every read through cloud compute.
""",
    },
    "Source Contracts": {
        "cluster": "Technical Concepts",
        "branch": "Data Plumbing",
        "summary": "Public feeds and the role each source plays.",
        "body": """
Each public source is treated as a contract with a grain, cadence, landing pattern, and Gold-layer usage. The contract is separate from runtime status. A source can be configured, actively landed, blocked, deferred, or unavailable.

Runtime source classification should be based on artifacts and pipeline status, not stale configuration text. If FDIC, QBP, FRED, or NIC artifacts exist and the corresponding flow passed, the technical surface should report that evidence clearly.
""",
    },
    "Warehouse Layers": {
        "cluster": "Technical Concepts",
        "branch": "Data Plumbing",
        "summary": "Bronze, Silver, Intermediate, and Gold boundaries.",
        "body": """
**Bronze** preserves source-shaped raw artifacts. **Silver** standardizes names, dates, identifiers, and types. **Intermediate** is reserved for reusable joins and business shaping. **Gold** is the dashboard contract consumed by Streamlit and the API.

The Interactive Data Browser exists to make those layers inspectable. It should let a reviewer choose a warehouse stage, choose a table in that stage, and preview a small read-only slice without modifying the data.
""",
    },
    "Orchestration And Modeling": {
        "cluster": "Technical Concepts",
        "branch": "Data Plumbing",
        "summary": "Where Airflow, dbt, Snowflake, DuckDB, and Streamlit fit.",
        "body": """
Airflow owns scheduling, dependencies, retry behavior, and run visibility. Python connectors perform acquisition. dbt owns SQL modeling, semantic shaping, and tests. Snowflake is the enterprise warehouse target. DuckDB keeps the system testable and demonstrable at low cost. Streamlit serves the analytical surfaces and FastAPI exposes machine-readable health.

The operating path is acquisition, raw landing, model build, quality checks, mart publication, and serving. The technical surface should expose enough evidence to prove those steps happened without drowning the viewer in raw logs.
""",
    },
    "Data Quality And Reconciliation": {
        "cluster": "Technical Concepts",
        "branch": "Controls",
        "summary": "Controls that make the numbers credible.",
        "body": """
The quality posture is based on source freshness, row counts, schema-aware contracts, dbt test artifacts, reconciliation checks, and read-only table previews.

Quality language must be precise. A table is passed, blocked, missing, or deferred. The application should not imply that a reconciliation or test ran if the source contract was not active or the artifact was not produced.
""",
    },
    "Deployment And Operations": {
        "cluster": "Technical Concepts",
        "branch": "Operations",
        "summary": "Serving model, health checks, monitoring, and domain strategy.",
        "body": """
Production runs through Docker Compose behind Caddy and Cloudflare. Streamlit serves the user-facing application, FastAPI exposes health status, and Uptime Kuma monitors service reachability.

The most reliable public route is a subdomain because Streamlit is naturally simpler at a root path. A route such as `/portfolio/FinLens` is possible, but it requires reverse-proxy and Streamlit base-path testing so assets and websocket paths resolve correctly.
""",
    },
    "Architecture Handbook": {
        "cluster": "Technical Concepts",
        "branch": "Architect Desk",
        "summary": "Full architecture decision register and technical handbook.",
        "body": """
This article contains the full architecture handbook. It is intentionally separated from the shorter Wiki articles so the handbook acts as a reference work instead of appearing as repeated appendix material under every article.
""",
        "render_handbook": True,
    },
}


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
    <div class="edge-credit">Built by Sri Surya S. Vaddhiparthy</div>
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
    if article.get("render_handbook"):
        render_architecture_decisions()
