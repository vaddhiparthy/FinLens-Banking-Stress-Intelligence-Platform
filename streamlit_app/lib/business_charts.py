"""Shared business-surface chart builders.

Pure functions (DataFrame -> Plotly figure) lifted out of the Stress Pulse, Failure Forensics, and
Macro Transmission pages so both those pages and the Business Dashboard render from one source. No
Streamlit calls here — just figure construction.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def add_recession_bands(figure: go.Figure) -> None:
    for start, end in (("2020Q1", "2020Q3"), ("2023Q1", "2023Q2")):
        figure.add_vrect(x0=start, x1=end, fillcolor="rgba(191, 109, 71, 0.08)",
                         line_width=0, layer="below")


def apply_readable_axes(figure: go.Figure) -> go.Figure:
    figure.update_xaxes(title_font=dict(color="#1f2933"), tickfont=dict(color="#1f2933"))
    figure.update_yaxes(title_font=dict(color="#1f2933"), tickfont=dict(color="#1f2933"))
    figure.update_layout(font=dict(color="#1f2933"))
    return figure


def has_chart_data(frame: pd.DataFrame, columns: list[str]) -> bool:
    return all(column in frame and frame[column].notna().any() for column in columns)


# ---- Stress Pulse ----
def earnings_chart(frame: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    figure.add_bar(x=frame["quarter"], y=frame["net_income"], name="Net income ($B)",
                   marker_color="#7c93a8")
    figure.add_scatter(x=frame["quarter"], y=frame["roa"], name="ROA (%)", mode="lines+markers",
                       yaxis="y2", line=dict(color="#bf6d47", width=2.5),
                       marker=dict(color="#bf6d47", size=6))
    figure.update_layout(
        margin=dict(l=10, r=10, t=40, b=10), xaxis_title="Quarter",
        yaxis_title="Net income ($B)", yaxis2=dict(title="ROA (%)", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0)",
        font=dict(color="#1f2933"))
    add_recession_bands(figure)
    return apply_readable_axes(figure)


def funding_chart(frame: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    figure.add_scatter(x=frame["quarter"], y=frame["asset_yield"], name="Yield on earning assets")
    figure.add_scatter(x=frame["quarter"], y=frame["funding_cost"], name="Cost of funds")
    figure.update_layout(
        margin=dict(l=10, r=10, t=40, b=10), legend=dict(orientation="h"),
        paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0)",
        font=dict(color="#1f2933"), xaxis_title="Quarter", yaxis_title="Rate (%)")
    add_recession_bands(figure)
    return apply_readable_axes(figure)


def nim_chart(frame: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    clean = frame.dropna(subset=["nim"])
    figure.add_scatter(x=clean["quarter"], y=clean["nim"], name="Net interest margin",
                       mode="lines+markers")
    figure.update_layout(
        margin=dict(l=10, r=10, t=40, b=10), legend=dict(orientation="h"),
        paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0)",
        font=dict(color="#1f2933"), xaxis_title="Quarter", yaxis_title="NIM (%)")
    add_recession_bands(figure)
    return apply_readable_axes(figure)


def asset_quality_chart(frame: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    figure.add_scatter(x=frame["quarter"], y=frame["noncurrent_rate"], name="Noncurrent loan rate")
    figure.add_scatter(x=frame["quarter"], y=frame["nco_rate"], name="Net charge-off rate", yaxis="y2")
    figure.update_layout(
        margin=dict(l=10, r=10, t=40, b=10), yaxis_title="Noncurrent (%)",
        yaxis2=dict(title="NCO (%)", overlaying="y", side="right"), legend=dict(orientation="h"),
        paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0)",
        font=dict(color="#1f2933"))
    add_recession_bands(figure)
    return apply_readable_axes(figure)


def unrealized_losses_chart(frame: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    figure.add_scatter(x=frame["quarter"], y=frame["afs_losses"], stackgroup="losses",
                       name="AFS unrealized gains/losses")
    figure.add_scatter(x=frame["quarter"], y=frame["htm_losses"], stackgroup="losses",
                       name="HTM unrealized gains/losses")
    figure.update_layout(
        margin=dict(l=10, r=10, t=40, b=10), legend=dict(orientation="h"),
        paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0)",
        font=dict(color="#1f2933"),
        annotations=[dict(x="2023Q1", y=-180, text="March 2023", showarrow=True, arrowhead=2)],
        xaxis_title="Quarter", yaxis_title="Unrealized gain/loss ($B)")
    add_recession_bands(figure)
    return apply_readable_axes(figure)


# ---- Failure Forensics ----
def failure_timeline(frame: pd.DataFrame) -> go.Figure:
    grouped = frame.groupby("year")["bank_id"].count().reset_index(name="failures")
    figure = px.bar(grouped, x="year", y="failures", color_discrete_sequence=["#bf6d47"])
    figure.update_layout(
        margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)", font=dict(color="#1f2933"),
        yaxis_title="Failures", xaxis_title="Failure year")
    return apply_readable_axes(figure)


def acquirer_chart(frame: pd.DataFrame) -> go.Figure:
    clean = frame.dropna(subset=["acquirer"]).copy()
    clean = clean.loc[clean["acquirer"].astype(str).str.strip() != ""]
    grouped = clean.groupby("acquirer").size().nlargest(15).reset_index(name="failures")
    figure = px.bar(grouped.sort_values("failures"), x="failures", y="acquirer", orientation="h",
                    color_discrete_sequence=["#0f766e"])
    figure.update_layout(
        title="Top acquirers in current filter", margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0)",
        font=dict(color="#1f2933"),
        xaxis=dict(title="Failures acquired", tickfont=dict(color="#1f2933")),
        yaxis=dict(title="Acquirer", tickfont=dict(color="#1f2933")))
    return apply_readable_axes(figure)


def state_map(frame: pd.DataFrame) -> go.Figure:
    if frame.empty:
        figure = go.Figure()
        figure.add_annotation(text="No failures match the selected filters", xref="paper",
                              yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(color="#1f2933"))
        figure.update_layout(margin=dict(l=10, r=10, t=30, b=10),
                             paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0)",
                             font=dict(color="#1f2933"))
        return figure
    value_column = "assets_millions" if frame["assets_millions"].notna().any() else "bank_id"
    aggregation = "sum" if value_column == "assets_millions" else "count"
    grouped = frame.groupby("state")[value_column].agg(aggregation).reset_index()
    figure = px.choropleth(grouped, locations="state", locationmode="USA-states",
                           color=value_column, scope="usa", color_continuous_scale="Tealgrn")
    figure.update_layout(
        title="State-wise failures in current filter", margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(255,255,255,0)", geo_bgcolor="rgba(255,255,255,0)",
        font=dict(color="#1f2933"),
        coloraxis_colorbar=dict(title="Failures", tickfont=dict(color="#1f2933")))
    return apply_readable_axes(figure)


# ---- Macro Transmission ----
def detail_chart(frame: pd.DataFrame, series: str) -> go.Figure:
    figure = go.Figure()
    clean = frame.dropna(subset=[series])
    figure.add_scatter(x=clean["date"], y=clean[series], name=series)
    figure.update_layout(
        title=f"{series} history", margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0)",
        font=dict(color="#1f2933"), xaxis=dict(title="Date", tickfont=dict(color="#1f2933")),
        yaxis=dict(title=series, tickfont=dict(color="#1f2933")))
    return apply_readable_axes(figure)


def failure_overlay_chart(frame: pd.DataFrame, series: str) -> go.Figure:
    figure = go.Figure()
    if series in frame and frame[series].notna().any():
        clean = frame.dropna(subset=[series])
        figure.add_scatter(x=clean["date"], y=clean[series], name=series, yaxis="y")
    if "failure_count" in frame:
        failures = frame.loc[frame["failure_count"].gt(0)]
        figure.add_bar(x=failures["date"], y=failures["failure_count"], name="Monthly failures",
                       yaxis="y2", marker_color="rgba(191, 109, 71, 0.45)")
    figure.update_layout(
        title=f"{series} with monthly FDIC failure counts", margin=dict(l=10, r=10, t=42, b=10),
        paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0)",
        font=dict(color="#1f2933"), xaxis=dict(title="Date", tickfont=dict(color="#1f2933")),
        yaxis=dict(title=series, tickfont=dict(color="#1f2933")),
        yaxis2=dict(title="Monthly failures", overlaying="y", side="right", rangemode="tozero",
                    tickfont=dict(color="#1f2933")),
        legend=dict(orientation="h"))
    return apply_readable_axes(figure)
