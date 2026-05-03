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

from streamlit_app.lib.data import load_failures, load_metrics, load_stress_pulse
from streamlit_app.lib.page_shell import BUSINESS_PAGE, page_intro, status_ribbon, top_navigation
from streamlit_app.lib.telemetry import record_page_view
from streamlit_app.lib.theme import app_css, ensure_theme_state, get_theme_mode
from streamlit_app.lib.ui_components import chart_note, inject_styles, section_heading, styled_table


def _source_catalog() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Source": "FDIC failed-bank feed",
                "What it means": "Official public record of institutions closed by regulators.",
                "Business use": "Shows when, where, and how bank failures cluster.",
                "FinLens transform": "Standardizes names, dates, state codes, acquirers, and failure years.",
            },
            {
                "Source": "FDIC Bank Data API summary",
                "What it means": "Industry aggregate balance-sheet and income values.",
                "Business use": "Provides the Stress Pulse baseline for assets, deposits, earnings, and loan stress.",
                "FinLens transform": "Converts thousands of dollars into readable billions and computes ratios.",
            },
            {
                "Source": "FDIC active institution metadata",
                "What it means": "Current insured-institution identity, state, regulator, and size attributes.",
                "Business use": "Explains the current bank universe behind the analytical platform.",
                "FinLens transform": "Creates a clean institution reference table for exploration and joins.",
            },
            {
                "Source": "FRED macro indicators",
                "What it means": "Public economic time series such as unemployment, rates, CPI, GDP, and housing.",
                "Business use": "Frames bank stress against the broader economy without claiming causality.",
                "FinLens transform": "Normalizes series into a common date-value panel for charts and lag views.",
            },
        ]
    )


def _metric_catalog() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Metric": "Net income",
                "Plain-language meaning": "Profit earned by the banking industry after expenses.",
                "How to read it": "Rising income is generally supportive; sudden compression can flag stress.",
            },
            {
                "Metric": "ROA",
                "Plain-language meaning": "Profit per dollar of assets.",
                "How to read it": "A cleaner profitability measure than raw dollars because it adjusts for size.",
            },
            {
                "Metric": "NIM",
                "Plain-language meaning": "Spread earned between asset income and funding costs.",
                "How to read it": "Compression can show pressure from deposit costs or lower asset yields.",
            },
            {
                "Metric": "Noncurrent rate",
                "Plain-language meaning": "Loans that are seriously past due or no longer accruing interest.",
                "How to read it": "This is an early sign of credit-quality deterioration.",
            },
            {
                "Metric": "Failure count",
                "Plain-language meaning": "Number of banks closed by regulators in a selected year or state.",
                "How to read it": "Useful for historical concentration, not a forward-looking prediction.",
            },
            {
                "Metric": "Yield curve spread",
                "Plain-language meaning": "Difference between long-term and short-term Treasury rates.",
                "How to read it": "Inversions are macro warning signs, but they are not bank-failure forecasts.",
            },
        ]
    )


def _insight_frame() -> pd.DataFrame:
    failures = load_failures()
    stress = load_stress_pulse()
    metrics = load_metrics()
    latest_failure_year = int(failures["year"].max()) if not failures.empty else None
    top_state = failures["state"].value_counts().index[0] if not failures.empty else "Not available"
    latest_income = stress["net_income"].dropna().iloc[-1] if not stress.empty else None
    series_count = metrics["series_id"].nunique() if not metrics.empty else 0
    return pd.DataFrame(
        [
            {
                "Question": "Where is failure history concentrated?",
                "Current answer": f"{top_state} has the highest failure count in the loaded FDIC history.",
                "How FinLens computed it": "Group standardized failed-bank rows by state and count institutions.",
            },
            {
                "Question": "What is the latest failure window?",
                "Current answer": f"The latest loaded failure year is {latest_failure_year}.",
                "How FinLens computed it": "Parse FDIC closing dates and derive a failure year column.",
            },
            {
                "Question": "What is the industry earnings baseline?",
                "Current answer": (
                    f"Latest aggregate net income is about ${latest_income:,.1f}B."
                    if latest_income is not None
                    else "QBP-style aggregate feed is not loaded."
                ),
                "How FinLens computed it": "Read FDIC aggregate values and convert thousands of dollars to billions.",
            },
            {
                "Question": "What macro context is available?",
                "Current answer": f"{series_count} FRED series are normalized into the macro panel.",
                "How FinLens computed it": "Load each FRED series into one date-value table with source labels.",
            },
        ]
    )


def _business_questions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Business question": "Is the banking system profitable at the aggregate level?",
                "Where to read it": "Stress Pulse",
                "Primary signals": "Net income, ROA, NIM, asset yield, funding cost",
                "What the dashboard contributes": "Places profitability beside funding pressure instead of showing an isolated KPI.",
            },
            {
                "Business question": "Where have failures concentrated historically?",
                "Where to read it": "Failure Forensics",
                "Primary signals": "Failure year, state, acquirer, failed-bank inventory",
                "What the dashboard contributes": "Turns the failure list into filterable geography and institutional drill-down.",
            },
            {
                "Business question": "Which macro signals are part of the current stress context?",
                "Where to read it": "Macro Transmission",
                "Primary signals": "Yield curve, unemployment, CPI, GDP, home prices",
                "What the dashboard contributes": "Separates each indicator onto its own scale and avoids false unit comparisons.",
            },
            {
                "Business question": "Can the numbers be traced back to stable public sources?",
                "Where to read it": "Technical Surface",
                "Primary signals": "Source artifacts, warehouse tables, reconciliation, dbt results",
                "What the dashboard contributes": "Shows how public data becomes a governed analytical layer.",
            },
        ]
    )


def _business_transform_rules() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Business entity": "Bank failure",
                "Raw source issue": "Names, dates, acquirers, and locations arrive as source-specific fields.",
                "Cleaned analytical form": "Bank, city, state, failure date, failure year, certificate, acquirer.",
                "Business benefit": "Users can filter failures by year/state and read a clean inventory.",
            },
            {
                "Business entity": "Industry aggregate",
                "Raw source issue": "FDIC aggregate values are not formatted for executive consumption.",
                "Cleaned analytical form": "Net income, ROA, NIM, losses, and quality ratios in readable units.",
                "Business benefit": "Stress Pulse reads like a banking health snapshot instead of a raw data extract.",
            },
            {
                "Business entity": "Macro indicator",
                "Raw source issue": "FRED series have different frequencies, units, labels, and date spans.",
                "Cleaned analytical form": "Curated indicator panel with date, indicator, latest value, and interpretation note.",
                "Business benefit": "Macro context is readable without pretending every line belongs on one axis.",
            },
            {
                "Business entity": "Analytical trust",
                "Raw source issue": "Users cannot easily tell whether a chart is live, stale, or manually entered.",
                "Cleaned analytical form": "Pipeline status, source artifacts, and quality tables tied to the same run state.",
                "Business benefit": "The dashboard explains not just what it shows, but why it should be trusted.",
            },
        ]
    )


def _reading_guide() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "If the viewer asks": "What is the fastest useful read?",
                "Recommended path": "Stress Pulse → Failure Forensics → Macro Transmission",
                "Reason": "This moves from system health to historical failures to economic context.",
            },
            {
                "If the viewer asks": "Where did the data come from?",
                "Recommended path": "Business Knowledge → Technical Surface",
                "Reason": "The business tab explains the meaning; the technical tab shows the operating controls.",
            },
            {
                "If the viewer asks": "Is this predicting bank failures?",
                "Recommended path": "Business Knowledge disclaimer and Macro Transmission interpretation notes",
                "Reason": "The app provides context and transformation, not regulatory ratings or predictions.",
            },
            {
                "If the viewer asks": "What changed from raw data to analytics?",
                "Recommended path": "Transformation Logic",
                "Reason": "The transformation tables explain standardization, scaling, cleaning, and metric shaping.",
            },
        ]
    )


st.set_page_config(
    page_title="FinLens | Business Knowledge",
    layout="wide",
    initial_sidebar_state="collapsed",
)
ensure_theme_state()
inject_styles(app_css(get_theme_mode(), sidebar_open=False))
top_navigation("business_docs", BUSINESS_PAGE)
record_page_view("business_knowledge", BUSINESS_PAGE)
status_ribbon("Business interpretation layer")
page_intro(
    "Business Surface",
    "Business Knowledge",
    "A plain-English guide to what the banking data means, what FinLens changes, and how to read "
    "the analysis without needing to be a banking specialist or data engineer.",
)

section_heading(
    "What FinLens Is Doing",
    "FinLens takes public banking and macroeconomic datasets, cleans their language and shape, "
    "loads them into analytical tables, and turns them into a small set of durable questions: "
    "how healthy is the industry, where did failures concentrate, and what macro conditions "
    "surrounded those periods.",
)
chart_note(
    "Business interpretation",
    "This is not a bank-failure prediction product. It is an analytical lens that organizes "
    "public facts into context, trends, and drill-downs.",
)

overview_tab, sources_tab, metrics_tab, transforms_tab, readouts_tab = st.tabs(
    [
        "Business Map",
        "Sources",
        "Metric Dictionary",
        "Transformation Logic",
        "Current Readouts",
    ]
)

with overview_tab:
    section_heading(
        "Business Question Map",
        "The business surface is organized around the questions a banking analyst or executive "
        "reviewer would ask first.",
    )
    styled_table(_business_questions())
    section_heading(
        "How To Read The Product",
        "Start with Stress Pulse for the industry baseline, use Failure Forensics for historical "
        "failure concentration, use Macro Transmission for economic context, and return here when "
        "a term or source needs translation.",
    )
    styled_table(_reading_guide())

with sources_tab:
    section_heading("Source Catalog", "The raw public sources and the business value each one adds.")
    styled_table(_source_catalog())

with metrics_tab:
    section_heading(
        "Metric Dictionary",
        "Key banking and macro terms translated into business language.",
    )
    styled_table(_metric_catalog())

with transforms_tab:
    section_heading(
        "Transformation Story",
        "The practical value is not just plotting public data. The value is converting inconsistent "
        "source language into stable analytical entities: institution, date, state, source, metric, "
        "and value.",
    )
    styled_table(_business_transform_rules())

with readouts_tab:
    section_heading(
        "Current Analytical Readouts",
        "Computed summaries from the active loaded data. These come from the warehouse tables rather "
        "than static prose.",
    )
    styled_table(_insight_frame())
