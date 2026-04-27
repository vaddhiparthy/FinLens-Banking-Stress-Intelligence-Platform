# ruff: noqa: E402

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").exists()
)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from streamlit_app.lib.data import load_failures, load_metrics
from streamlit_app.lib.page_shell import BUSINESS_PAGE, page_intro, status_ribbon, top_navigation
from streamlit_app.lib.telemetry import record_page_view
from streamlit_app.lib.theme import app_css, ensure_theme_state, get_palette, get_theme_mode
from streamlit_app.lib.ui_components import inject_styles, metric_card, section_heading

SERIES_LABELS = {
    "UNRATE": "Unemployment",
    "DGS10": "10Y Treasury",
    "DGS2": "2Y Treasury",
    "BAA": "BAA Yield",
    "BAA10Y": "BAA-10Y Spread",
    "NFCI": "NFCI",
}


def _format_metric(value: object, suffix: str = "") -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if pd.isna(numeric):
        return "N/A"
    return f"{numeric:.2f}{suffix}"


def build_macro_panel() -> pd.DataFrame:
    metrics = load_metrics().copy()
    metrics["series_label"] = metrics["series_id"].map(SERIES_LABELS).fillna(
        metrics["metric_name"]
    )
    pivot = metrics.pivot_table(
        index="date",
        columns="series_label",
        values="value",
        aggfunc="last",
    )
    pivot = pivot.sort_index().reset_index()
    if "10Y Treasury" in pivot and "2Y Treasury" in pivot:
        pivot["10Y-2Y"] = pivot["10Y Treasury"] - pivot["2Y Treasury"]
    if "BAA Yield" in pivot and "10Y Treasury" in pivot and "BAA-AAA Spread" not in pivot:
        pivot["BAA Spread"] = pivot["BAA Yield"] - pivot["10Y Treasury"]
    elif "BAA10Y" in pivot:
        pivot["BAA Spread"] = pivot["BAA10Y"]
    else:
        pivot["BAA Spread"] = pd.NA
    if "Unemployment" not in pivot and "Unemployment Rate" in pivot:
        pivot["Unemployment"] = pivot["Unemployment Rate"]
    if "NFCI" not in pivot:
        pivot["NFCI"] = pd.NA
    return pivot


def failure_count_series(frame: pd.DataFrame) -> pd.DataFrame:
    failures = load_failures().copy()
    if "closing_date" in failures.columns:
        failures["closing_date"] = pd.to_datetime(failures["closing_date"], errors="coerce")
        failures = failures.dropna(subset=["closing_date"])
        if not failures.empty:
            monthly = (
                failures.assign(
                    month=lambda data: data["closing_date"].dt.to_period("M").dt.to_timestamp()
                )
                .groupby("month")
                .size()
                .reset_index(name="failure_count")
            )
            merged = frame.merge(monthly, left_on="date", right_on="month", how="left")
            merged["failure_count"] = merged["failure_count"].fillna(0)
            return merged.drop(columns=["month"])
    frame["failure_count"] = 0
    return frame


def lag_heatmap(frame: pd.DataFrame) -> go.Figure:
    palette = get_palette()
    series_names = [
        name for name in ["10Y-2Y", "NFCI", "BAA Spread", "Unemployment"] if name in frame
    ]
    lags = [0, 4, 8, 12, 18, 24]
    z_values: list[list[float]] = []
    for series_name in series_names:
        row: list[float] = []
        for lag in lags:
            shifted = frame[series_name].shift(lag)
            correlation = shifted.corr(frame["failure_count"])
            row.append(0.0 if pd.isna(correlation) else float(abs(correlation)))
        z_values.append(row)
    figure = go.Figure(
        data=go.Heatmap(
            z=z_values,
            x=[f"{lag}m" for lag in lags],
            y=series_names,
            colorscale=[
                [0.0, palette["sand"]],
                [0.5, palette["teal_soft"]],
                [1.0, palette["accent"]],
            ],
            zmin=0,
            zmax=max([max(row) for row in z_values], default=0.45) or 0.45,
        )
    )
    figure.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
    )
    return figure


def detail_chart(frame: pd.DataFrame, series: str) -> go.Figure:
    figure = go.Figure()
    figure.add_scatter(x=frame["date"], y=frame[series], name=series)
    figure.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
    )
    return figure


def yield_curve_chart(frame: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    figure.add_scatter(x=frame["date"], y=frame["10Y-2Y"], name="10Y-2Y spread")
    figure.add_hline(y=0, line_dash="dash")
    figure.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
    )
    return figure


st.set_page_config(
    page_title="FinLens | Macro Transmission",
    layout="wide",
    initial_sidebar_state="collapsed",
)
ensure_theme_state()
inject_styles(app_css(get_theme_mode(), sidebar_open=False))
top_navigation("metrics", BUSINESS_PAGE)
record_page_view("macro_transmission", BUSINESS_PAGE)
status_ribbon("Macro context view")
page_intro(
    "Business Surface",
    "Macro Transmission",
    "This page stays narrow on purpose: only stable macro indicators, a simple lag view, and the "
    "clearest stress signals that can support a long-lived dashboard.",
)

frame = build_macro_panel()
frame = failure_count_series(frame)
available_series = [
    name for name in ["10Y-2Y", "NFCI", "BAA Spread", "Unemployment"] if name in frame
]
selected_series = st.selectbox("Indicator detail", available_series)
latest = frame.iloc[-1]

card1, card2, card3, card4 = st.columns(4)
with card1:
    metric_card("10Y-2Y", _format_metric(latest["10Y-2Y"]), "Latest monthly reading")
with card2:
    metric_card("NFCI", _format_metric(latest.get("NFCI")), "Current financial conditions")
with card3:
    metric_card("BAA spread", _format_metric(latest["BAA Spread"]), "Credit stress signal")
with card4:
    metric_card(
        "Unemployment",
        _format_metric(latest["Unemployment"], "%"),
        "Current labor backdrop",
    )

section_heading(
    "Lag Heatmap",
    "The MVP keeps this honest: a compact, documented heatmap of simple historical lead-lag "
    "relationships rather than causal storytelling.",
)
st.plotly_chart(lag_heatmap(frame), width="stretch")

section_heading(
    "Indicator Detail",
    "Selecting a series opens the simplest useful drill-down: the indicator itself and the "
    "most familiar stress view, the yield curve.",
)
left, right = st.columns(2)
with left:
    st.plotly_chart(detail_chart(frame, selected_series), width="stretch")
with right:
    st.plotly_chart(yield_curve_chart(frame), width="stretch")
