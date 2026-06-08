"""Shared data-engineering pipeline visuals (Sankey + status table) used by both the Data
Engineering surface and the Technical Dashboard, so the "Run status by flow" chart and the
last-run status table are defined once and rendered identically in both places."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go

from finlens.pipeline_status import pipeline_status_rows
from streamlit_app.lib.theme import get_palette

# Timezone options for the "Last run" column. Labels are friendly; values are IANA names whose
# abbreviation (EDT/EST, etc.) is resolved at format time so DST is always correct.
TZ_CHOICES = {
    "Eastern (ET)": "America/New_York",
    "Central (CT)": "America/Chicago",
    "Mountain (MT)": "America/Denver",
    "Pacific (PT)": "America/Los_Angeles",
    "UTC": "UTC",
}


def pipeline_status_frame() -> pd.DataFrame:
    return pd.DataFrame(pipeline_status_rows())


def _status_color(status: str, palette: dict[str, str]) -> str:
    return {
        "Success": "rgba(121, 183, 175, 0.55)",
        "Failed": "rgba(212, 139, 102, 0.55)",
        "Running": "rgba(179, 141, 91, 0.55)",
        "Missing Data": "rgba(180, 170, 156, 0.5)",
        "Deferred": "rgba(180, 170, 156, 0.35)",
        "Not Activated": "rgba(180, 170, 156, 0.35)",
    }.get(status, palette["text_soft"])


def dag_chart(frame: pd.DataFrame) -> go.Figure:
    palette = get_palette()
    link_colors = []
    link_labels = []
    for row in frame.itertuples():
        color = _status_color(row.status, palette)
        link_colors.append(color)
        link_labels.append(f"{row.flow_no}. {row.flow_name}, {row.status}")
    figure = go.Figure(
        go.Sankey(
            arrangement="snap",
            node=dict(
                label=["FDIC", "QBP", "FRED", "NIC", "Bronze", "Silver", "Gold", "Dashboards"],
                pad=18,
                thickness=18,
                color=[
                    palette["accent"],
                    "rgba(180, 170, 156, 0.7)",
                    palette["link"],
                    "rgba(180, 170, 156, 0.7)",
                    palette["accent_soft"],
                    palette["teal_soft"],
                    palette["content_bg"],
                    palette["rose"],
                ],
            ),
            link=dict(
                source=[0, 1, 2, 3, 4, 5, 6],
                target=[4, 4, 4, 4, 5, 6, 7],
                value=[4, 4, 4, 3, 6, 6, 6],
                color=link_colors,
                label=link_labels,
            ),
        )
    )
    figure.update_layout(
        height=360,  # reserve space to avoid layout shift (CLS) as the chart streams in
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        font=dict(color="#1f2933"),
    )
    return figure


def fmt_last_run(v: object, tz_name: str = "America/New_York") -> str:
    """Render an ISO run timestamp in the chosen timezone (with its abbreviation); pass through
    non-timestamps (e.g. 'Source contract inactive', '—') unchanged."""
    if not isinstance(v, str) or "T" not in v:
        return str(v)
    try:
        dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        local = dt.astimezone(ZoneInfo(tz_name))
        return f"{local.strftime('%b %d, %Y · %H:%M')} {local.strftime('%Z')}"
    except Exception:  # noqa: BLE001
        return str(v)


def pipeline_status_table(frame: pd.DataFrame, tz_name: str = "America/New_York") -> pd.DataFrame:
    indicator_map = {
        "Success": "🟢 Success",
        "Failed": "🔴 Failed",
        "Running": "🟠 Running",
        "Missing Data": "⚪ Missing Data",
        "Deferred": "⚪ Deferred",
        "Not Activated": "⚪ Not Activated",
    }
    # Honest runtime: the extractors were run by scripts/run_local_pipeline.py (Python), not a
    # live Airflow scheduler. The Airflow DAGs are defined (airflow/dags/) for scheduled runs.
    tool_map = {
        "FDIC -> Bronze": "Python extractor (local run; Airflow DAG defined)",
        "QBP -> Bronze": "FDIC summary extractor (local run; Airflow DAG defined)",
        "FRED -> Bronze": "FRED extractor (local run; Airflow DAG defined)",
        "NIC -> Bronze": "Institution-metadata extractor (local run; Airflow DAG defined)",
        "Bronze -> Silver": "dbt staging / canonical model",
        "Silver -> Gold": "dbt mart build",
        "Gold -> Dashboards": "DuckDB mart read + Streamlit",
    }
    artifact_map = {
        "FDIC -> Bronze": "FDIC failure feed is landing into the active data contract",
        "QBP -> Bronze": "FDIC aggregate banking summary lands into the active data contract",
        "FRED -> Bronze": "FRED macro series are landing into the active data contract",
        "NIC -> Bronze": "FDIC active-institution metadata lands into the active data contract",
        "Bronze -> Silver": "Canonical model layer rebuilds from source payloads",
        "Silver -> Gold": "Dashboard-facing marts are refreshed from canonical tables",
        "Gold -> Dashboards": "FastAPI health and Streamlit serving are live",
    }
    return frame.assign(
        status_label=lambda data: data["status"].map(indicator_map),
        execution_tool=lambda data: data["flow_name"].map(tool_map),
        runtime_artifact=lambda data: data["flow_name"].map(artifact_map),
        last_run=lambda data: data["last_run"].map(lambda v: fmt_last_run(v, tz_name)),
    )[
        [
            "flow_no",
            "flow_name",
            "execution_tool",
            "status_label",
            "last_run",
            "rows",
            "runtime_artifact",
        ]
    ].rename(
        columns={
            "flow_no": "#",
            "flow_name": "Data flow",
            "execution_tool": "Tool / runtime",
            "status_label": "Status",
            "last_run": "Last run",
            "rows": "Rows / units",
            "runtime_artifact": "Operational artifact",
        }
    )
