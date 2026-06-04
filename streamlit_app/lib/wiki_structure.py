"""Encyclopedia structure for the FinLens Wiki.

Defines the section -> (subsection) -> article taxonomy, merges the base article
corpus with any deepened/new articles, and exposes helpers for the Wikipedia-style
one-article-per-page UI (slugs, lookup, sidebar tree, corpus statistics).

The ordering is a deliberate read-through: Introduction, then the Business domain,
then the platform Architecture, then Data Engineering (with sub-groups), then
AI Engineering, then Reference.
"""

from __future__ import annotations

from streamlit_app.lib.wiki_content import ARTICLES as _BASE
from streamlit_app.lib.wiki_extra import EXTRA_ARTICLES as _EXTRA

# Deepened/new article modules authored separately; merged if present so a missing
# file never breaks the wiki. Later dicts override earlier ones by title.
try:
    from streamlit_app.lib.wiki_de_articles import DE_ARTICLES as _DE
except Exception:
    _DE = {}
try:
    from streamlit_app.lib.wiki_ai_articles import AI_ARTICLES as _AI
except Exception:
    _AI = {}

# Merged corpus. Extra/deepened articles override base entries with the same title.
ARTICLES: dict[str, dict] = {**_BASE, **_EXTRA, **_DE, **_AI}

# section_id, section title, [(subsection title or None, [article titles in order])]
SECTIONS: list[tuple[str, str, list[tuple[str | None, list[str]]]]] = [
    ("introduction", "Introduction", [
        (None, [
            "What FinLens Is",
            "The Problem: Bank Financial Distress",
            "How This Wiki Is Organized",
        ]),
    ]),
    ("business", "Business", [
        (None, [
            "Banking Industry Stress, Defined",
            "Aggregate Profitability Metrics",
            "Asset Quality and Credit Stress",
            "Capital, Unrealised Losses, and the 2023 Episode",
            "Reading Failed-Bank Records",
            "Macroeconomic Context and Banking Stress",
            "How to Read Macro Indicators in This Surface",
            "What the Failure Surface Cannot Show",
            "What Macro Data Cannot Prove",
        ]),
    ]),
    ("architecture", "Architecture", [
        (None, [
            "Platform Architecture",
            "The Three Surfaces",
            "Bronze, Silver, Intermediate, Gold",
            "Why Dashboards Read Gold Only",
            "Tooling Choices and Their Rationale",
        ]),
    ]),
    ("data-engineering", "Data Engineering", [
        ("Sources", [
            "Source Policy Overview",
            "FDIC BankFind",
            "FDIC Quarterly Banking Profile",
            "FRED and ALFRED",
            "National Information Center",
            "Excluded Sources and Their Rationale",
        ]),
        ("Warehouse", [
            "Snowflake Warehouse Topology",
            "dbt Model Inventory",
            "Tests and the Data Quality Boundary",
        ]),
        ("Orchestration", [
            "Airflow DAG Topology",
            "Why the DAGs Are Thin",
            "Local Parity",
        ]),
        ("Quality & Reconciliation", [
            "Reconciliation Against External Authority",
            "Data Quality Strategy",
            "Pipeline Status and Operational State",
        ]),
        ("Serving & Operations", [
            "Streamlit Surfaces",
            "FastAPI Endpoints",
            "Edge and Operations",
            "Deployment Topology",
            "Configuration and Secrets",
            "Monitoring and Health",
        ]),
    ]),
    ("ai-engineering", "AI Engineering", [
        ("Modelling", [
            "Problem Framing: Discrete-Time Hazard",
            "Feature Engineering and the Monotone Contract",
            "Labelling and Leakage Control",
        ]),
        ("Evaluation & Calibration", [
            "Out-of-Time Evaluation",
            "Probability Calibration",
            "Explainability with SHAP",
        ]),
        ("Governance & Operations", [
            "Model Risk and Governance",
            "Drift Monitoring",
            "Serving the Model",
        ]),
        ("Predictive Analytics", [
            "Predictive Analytics on Currently Operating Banks",
            "Engineering of the Predictive Pipeline",
            "How to Read a Stress Score",
        ]),
    ]),
    ("reference", "Reference", [
        (None, [
            "Glossary",
            "External References",
        ]),
    ]),
]


def slug(title: str) -> str:
    return title.lower().replace("&", "and").replace(",", "").replace(":", "").replace(
        "(", "").replace(")", "").replace("/", "-").replace(" ", "-")


_SLUG_TO_TITLE = {slug(t): t for t in ARTICLES}


def title_for_slug(s: str) -> str | None:
    return _SLUG_TO_TITLE.get(s)


def article(title: str) -> dict | None:
    return ARTICLES.get(title)


def section_of(title: str) -> tuple[str, str] | None:
    """Return (section_id, section_title) for an article title."""
    for sid, stitle, groups in SECTIONS:
        for _sub, titles in groups:
            if title in titles:
                return sid, stitle
    return None


def all_titles_in_order() -> list[str]:
    out: list[str] = []
    for _sid, _stitle, groups in SECTIONS:
        for _sub, titles in groups:
            out.extend(t for t in titles if t in ARTICLES)
    return out


def neighbours(title: str) -> tuple[str | None, str | None]:
    order = all_titles_in_order()
    if title not in order:
        return None, None
    i = order.index(title)
    prev = order[i - 1] if i > 0 else None
    nxt = order[i + 1] if i < len(order) - 1 else None
    return prev, nxt


def stats() -> dict:
    titles = all_titles_in_order()
    words = sum(len(ARTICLES[t]["body"].split()) for t in titles)
    return {
        "articles": len(titles),
        "sections": len(SECTIONS),
        "words": words,
        "read_minutes": max(1, round(words / 220)),
    }
