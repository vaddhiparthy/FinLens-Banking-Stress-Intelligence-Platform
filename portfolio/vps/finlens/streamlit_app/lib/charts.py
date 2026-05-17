from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from streamlit_app.lib.theme import get_palette


def chart_frame() -> dict:
    palette = get_palette()
    return {
        "plot_bgcolor": "rgba(255,255,255,0)",
        "paper_bgcolor": "rgba(255,255,255,0)",
        "margin": dict(l=10, r=10, t=60, b=10),
        "font": dict(color=palette["text_main"]),
        "title_font": dict(color=palette["text_main"], size=18),
        "height": 340,
    }


def failures_by_year_chart(filtered_failures: pd.DataFrame):
    palette = get_palette()
    failures_by_year = (
        filtered_failures.groupby("year", as_index=False)["bank_id"]
        .count()
        .rename(columns={"bank_id": "failures"})
    )
    fig = px.bar(
        failures_by_year,
        x="year",
        y="failures",
        text="failures",
        color_discrete_sequence=[palette["teal"]],
    )
    fig.update_traces(textposition="inside", insidetextanchor="middle", cliponaxis=False)
    fig.update_layout(title="Failed Banks by Year", bargap=0.34, **chart_frame())
    for year, label in [(2008, "Global crisis"), (2023, "Regional bank shock")]:
        if year in failures_by_year["year"].tolist():
            value = int(failures_by_year.loc[failures_by_year["year"] == year, "failures"].iloc[0])
            fig.add_annotation(
                x=year,
                y=value,
                text=label,
                showarrow=True,
                arrowhead=2,
                ay=-48,
                bgcolor="rgba(255,255,255,.85)",
            )
    return fig


def state_assets_map(filtered_failures: pd.DataFrame):
    palette = get_palette()
    state_assets = (
        filtered_failures.groupby("state", as_index=False)["assets_millions"]
        .sum()
        .sort_values("assets_millions", ascending=False)
    )
    fig = px.choropleth(
        state_assets,
        locations="state",
        locationmode="USA-states",
        color="assets_millions",
        scope="usa",
        color_continuous_scale=[
            palette["sand"],
            "#d5b98d",
            palette["accent"],
            palette["rose"],
        ],
    )
    fig.update_layout(
        title="Failed Bank Assets by State",
        geo_bgcolor="rgba(255,255,255,0)",
        paper_bgcolor="rgba(255,255,255,0)",
        margin=dict(l=0, r=0, t=60, b=0),
        height=360,
        coloraxis_colorbar=dict(
            title="Assets (M)",
            thickness=12,
            len=0.24,
            y=0.02,
            yanchor="bottom",
            x=0.5,
            xanchor="center",
        ),
    )
    return fig


def macro_trend_chart(filtered_metrics: pd.DataFrame, selected_metric: str):
    palette = get_palette()
    fig = px.line(
        filtered_metrics.sort_values("date"),
        x="date",
        y="value",
        markers=True,
        color_discrete_sequence=[palette["link"]],
    )
    fig.update_layout(
        title=f"{selected_metric} Trend",
        yaxis_title="Metric value",
        xaxis_title="Date",
        **chart_frame(),
    )
    return fig


def acquirer_chart(filtered_acquirers: pd.DataFrame):
    palette = get_palette()
    fig = px.bar(
        filtered_acquirers.sort_values("assets_absorbed_millions", ascending=True),
        x="assets_absorbed_millions",
        y="acquirer",
        orientation="h",
        color="decade",
        color_discrete_sequence=[palette["accent"], palette["link"]],
    )
    fig.update_layout(
        title="Top Acquirers by Assets Absorbed",
        xaxis_title="Assets absorbed (millions USD)",
        yaxis_title="",
        showlegend=False,
        **(chart_frame() | {"height": 310}),
    )
    return fig


def state_mix_donut(filtered_failures: pd.DataFrame):
    palette = get_palette()
    summary = (
        filtered_failures.groupby("state", as_index=False)["bank_id"]
        .count()
        .rename(columns={"bank_id": "failures"})
        .sort_values("failures", ascending=False)
    )
    fig = go.Figure(
        data=[
            go.Pie(
                labels=summary["state"],
                values=summary["failures"],
                hole=0.62,
                marker=dict(
                    colors=[
                        palette["link"],
                        palette["accent"],
                        "#d5b98d",
                        "#8ba5a0",
                    ]
                ),
            )
        ]
    )
    fig.update_layout(
        title="Failure Mix by State",
        paper_bgcolor="rgba(255,255,255,0)",
        margin=dict(l=10, r=10, t=60, b=10),
        showlegend=True,
        height=310,
    )
    return fig


def top_states_chart(filtered_failures: pd.DataFrame):
    palette = get_palette()
    summary = (
        filtered_failures.groupby("state", as_index=False)["bank_id"]
        .count()
        .rename(columns={"bank_id": "failures"})
        .sort_values("failures", ascending=False)
        .head(7)
    )
    fig = px.bar(
        summary,
        x="state",
        y="failures",
        text="failures",
        color_discrete_sequence=[palette["accent"]],
    )
    fig.update_traces(textposition="inside", cliponaxis=False)
    fig.update_layout(title="Most Failure-Exposed States", bargap=0.34, **chart_frame())
    return fig


def largest_failures_chart(filtered_failures: pd.DataFrame):
    palette = get_palette()
    summary = filtered_failures.sort_values("assets_millions", ascending=True).tail(6)
    fig = px.bar(
        summary,
        x="assets_millions",
        y="bank_name",
        orientation="h",
        color_discrete_sequence=[palette["link"]],
    )
    fig.update_layout(
        title="Largest Historical Failures in Scope",
        xaxis_title="Assets (millions USD)",
        yaxis_title="",
        **(chart_frame() | {"height": 310}),
    )
    return fig


def macro_compare_chart(metrics: pd.DataFrame):
    palette = get_palette()
    frame = metrics.copy()
    frame["value_index"] = frame.groupby("series_id")["value"].transform(
        lambda series: (series / series.iloc[0]) * 100 if series.iloc[0] != 0 else 100.0
    )
    fig = px.line(
        frame.sort_values("date"),
        x="date",
        y="value_index",
        color="metric_name",
        markers=False,
        line_shape="spline",
        color_discrete_sequence=[palette["link"], palette["accent"], palette["teal"]],
    )
    fig.update_layout(
        title="Indexed Macro Regime Comparison",
        yaxis_title="Index (first observation = 100)",
        xaxis_title="Date",
        legend_title="Series",
        **(chart_frame() | {"height": 340}),
    )
    return fig


def latest_macro_snapshot(metrics: pd.DataFrame):
    palette = get_palette()
    latest = (
        metrics.sort_values("date")
        .groupby(["series_id", "metric_name"], as_index=False)
        .tail(1)
        .sort_values("value", ascending=True)
    )
    fig = px.bar(
        latest,
        x="value",
        y="metric_name",
        orientation="h",
        color="metric_name",
        color_discrete_sequence=[palette["accent"], palette["link"], palette["teal"]],
    )
    fig.update_layout(
        title="Latest Macro Snapshot",
        xaxis_title="Latest observed value",
        yaxis_title="",
        showlegend=False,
        **(chart_frame() | {"height": 310}),
    )
    return fig
