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
from streamlit_app.lib.theme import app_css, ensure_theme_state, get_theme_mode
from streamlit_app.lib.ui_components import (
    chart_note,
    empty_state,
    inject_styles,
    metric_card,
    section_heading,
    styled_table,
)

SERIES_LABELS = {
    "UNRATE": "Unemployment",
    "DGS10": "10Y Treasury",
    "DGS2": "2Y Treasury",
    "GDP": "GDP",
    "CPIAUCSL": "CPI",
    "CSUSHPINSA": "Home Price Index",
}


def apply_readable_axes(figure: go.Figure) -> go.Figure:
    figure.update_xaxes(title_font=dict(color="#1f2933"), tickfont=dict(color="#1f2933"))
    figure.update_yaxes(title_font=dict(color="#1f2933"), tickfont=dict(color="#1f2933"))
    figure.update_layout(font=dict(color="#1f2933"))
    return figure


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
    if "Unemployment" not in pivot and "Unemployment Rate" in pivot:
        pivot["Unemployment"] = pivot["Unemployment Rate"]
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


def indicator_board(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    metadata = {
        "10Y-2Y": ("Yield curve slope", "Rates", "Negative values indicate inversion."),
        "Unemployment": ("Labor market stress", "Labor", "Higher values usually pressure credit."),
        "CPI": ("Inflation level", "Prices", "Level index; not comparable to rates."),
        "GDP": ("Economic activity", "Growth", "Quarterly level series."),
        "Home Price Index": ("Housing collateral context", "Asset prices", "Level index."),
    }
    for series, (description, family, note) in metadata.items():
        if series not in frame or frame[series].dropna().empty:
            continue
        valid = frame.dropna(subset=[series])
        latest = valid.iloc[-1]
        rows.append(
            {
                "Indicator": series,
                "Family": family,
                "Latest": _format_metric(latest[series]),
                "As of": str(latest["date"].date()),
                "Use": description,
                "Note": note,
            }
        )
    return pd.DataFrame(rows)


def detail_chart(frame: pd.DataFrame, series: str) -> go.Figure:
    figure = go.Figure()
    clean = frame.dropna(subset=[series])
    figure.add_scatter(x=clean["date"], y=clean[series], name=series)
    figure.update_layout(
        title=f"{series} history",
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        font=dict(color="#1f2933"),
        xaxis=dict(title="Date", tickfont=dict(color="#1f2933")),
        yaxis=dict(title=series, tickfont=dict(color="#1f2933")),
    )
    return apply_readable_axes(figure)


def failure_overlay_chart(frame: pd.DataFrame, series: str) -> go.Figure:
    figure = go.Figure()
    if series in frame and frame[series].notna().any():
        clean = frame.dropna(subset=[series])
        figure.add_scatter(x=clean["date"], y=clean[series], name=series, yaxis="y")
    if "failure_count" in frame:
        failures = frame.loc[frame["failure_count"].gt(0)]
        figure.add_bar(
            x=failures["date"],
            y=failures["failure_count"],
            name="Monthly failures",
            yaxis="y2",
            marker_color="rgba(191, 109, 71, 0.45)",
        )
    figure.update_layout(
        title=f"{series} with monthly FDIC failure counts",
        margin=dict(l=10, r=10, t=42, b=10),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        font=dict(color="#1f2933"),
        xaxis=dict(title="Date", tickfont=dict(color="#1f2933")),
        yaxis=dict(title=series, tickfont=dict(color="#1f2933")),
        yaxis2=dict(
            title="Monthly failures",
            overlaying="y",
            side="right",
            rangemode="tozero",
            tickfont=dict(color="#1f2933"),
        ),
        legend=dict(orientation="h"),
    )
    return apply_readable_axes(figure)


def available_macro_series(frame: pd.DataFrame) -> list[str]:
    return [
        name
        for name in ["10Y-2Y", "Unemployment", "CPI", "GDP", "Home Price Index"]
        if name in frame and frame[name].notna().any()
    ]


def latest_metric(frame: pd.DataFrame, series: str, suffix: str = "") -> tuple[str, str]:
    if series not in frame:
        return "Available after source refresh", series
    valid = frame.dropna(subset=[series])
    if valid.empty:
        return "Available after source refresh", series
    latest = valid.iloc[-1]
    return _format_metric(latest[series], suffix), str(latest["date"].date())


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
available_series = available_macro_series(frame)
if not available_series:
    empty_state("No FRED observations are available from the current source run.")
    st.stop()

card1, card2, card3, card4 = st.columns(4)
with card1:
    value, as_of = latest_metric(frame, "10Y-2Y")
    metric_card("10Y-2Y", value, f"As of {as_of}")
with card2:
    value, as_of = latest_metric(frame, "Unemployment", "%")
    metric_card("Unemployment", value, f"As of {as_of}")
with card3:
    value, as_of = latest_metric(frame, "CPI")
    metric_card("CPI", value, f"As of {as_of}")
with card4:
    value, as_of = latest_metric(frame, "Home Price Index")
    metric_card("Home Price Index", value, f"As of {as_of}")

section_heading(
    "Macro Stress Drill-Down",
    "Choose one macro signal, then read it two ways: first on its own native scale, then beside "
    "monthly FDIC failure counts on a separate axis.",
)
selected_series = st.selectbox(
    "Select macro signal",
    available_series,
    key="macro_signal_selector",
)

left, right = st.columns(2)
with left:
    st.plotly_chart(detail_chart(frame, selected_series), width="stretch")
    chart_note(
        "Interpretation",
        f"This chart isolates {selected_series} on its own native scale so the line shape is not "
        "distorted by unrelated units.",
    )
with right:
    st.plotly_chart(failure_overlay_chart(frame, selected_series), width="stretch")
    chart_note(
        "Interpretation",
        "Bars show monthly FDIC failures on the right axis. The overlay is context only; it is not "
        "a causal model or prediction.",
    )

section_heading(
    "Indicator Board",
    "These are the stable FRED indicators currently loaded into gold. They are summarized after "
    "the drill-down because the charts are the primary analytical interaction on this page.",
)
styled_table(indicator_board(frame))
