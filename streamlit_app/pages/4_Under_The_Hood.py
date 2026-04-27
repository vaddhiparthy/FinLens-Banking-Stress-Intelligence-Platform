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

from finlens.config import get_settings
from finlens.pipeline_status import pipeline_status_rows
from finlens.state import load_state
from finlens.telemetry import telemetry_summary
from finlens.warehouse import stress_pulse_source_mode
from streamlit_app.lib.architecture_docs import render_architecture_decisions
from streamlit_app.lib.page_shell import (
    TECHNICAL_PAGE,
    get_technical_section,
    page_intro,
    status_ribbon,
    top_navigation,
)
from streamlit_app.lib.telemetry import record_page_view
from streamlit_app.lib.theme import app_css, ensure_theme_state, get_palette, get_theme_mode
from streamlit_app.lib.ui_components import (
    inject_styles,
    metric_card,
    section_heading,
    styled_table,
    tech_bulletin,
)


def pipeline_status_frame() -> pd.DataFrame:
    return pd.DataFrame(pipeline_status_rows())


def _status_color(status: str, palette: dict[str, str]) -> str:
    return {
        "Success": "rgba(121, 183, 175, 0.55)",
        "Failed": "rgba(212, 139, 102, 0.55)",
        "Running": "rgba(179, 141, 91, 0.55)",
        "Missing Data": "rgba(180, 170, 156, 0.5)",
        "Deferred": "rgba(180, 170, 156, 0.35)",
    }.get(status, palette["text_soft"])


def dag_chart(frame: pd.DataFrame) -> go.Figure:
    palette = get_palette()
    link_colors = []
    link_labels = []
    for row in frame.itertuples():
        color = _status_color(row.status, palette)
        link_colors.append(color)
        link_labels.append(f"{row.flow_no}. {row.flow_name} — {row.status}")
    figure = go.Figure(
        go.Sankey(
            arrangement="snap",
            node=dict(
                label=[
                    "FDIC",
                    "QBP deferred",
                    "FRED",
                    "NIC deferred",
                    "Bronze",
                    "Silver",
                    "Gold",
                    "Dashboards",
                ],
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
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        font=dict(color="#1f2933"),
    )
    return figure


def pipeline_status_table(frame: pd.DataFrame) -> pd.DataFrame:
    indicator_map = {
        "Success": "🟢 Success",
        "Failed": "🔴 Failed",
        "Running": "🟠 Running",
        "Missing Data": "⚪ Missing Data",
        "Deferred": "⚪ Deferred",
    }
    tool_map = {
        "FDIC -> Bronze": "Airflow task + Python extractor",
        "QBP -> Bronze": "Airflow task (deferred)",
        "FRED -> Bronze": "Airflow task + FRED extractor",
        "NIC -> Bronze": "Airflow task (deferred)",
        "Bronze -> Silver": "dbt staging / canonical model",
        "Silver -> Gold": "dbt mart build",
        "Gold -> Dashboards": "Snowflake/DuckDB mart read + Streamlit",
    }
    evidence_map = {
        "FDIC -> Bronze": "FDIC failure feed is landing into the active data contract",
        "QBP -> Bronze": "Not active in zero-risk source scope",
        "FRED -> Bronze": "FRED macro series are landing into the active data contract",
        "NIC -> Bronze": "Not active in zero-risk source scope",
        "Bronze -> Silver": "Canonical model layer rebuilds from source payloads",
        "Silver -> Gold": "Dashboard-facing marts are refreshed from canonical tables",
        "Gold -> Dashboards": "FastAPI health and Streamlit serving are live",
    }
    return frame.assign(
        status_label=lambda data: data["status"].map(indicator_map),
        execution_tool=lambda data: data["flow_name"].map(tool_map),
        runtime_evidence=lambda data: data["flow_name"].map(evidence_map),
    )[
        [
            "flow_no",
            "flow_name",
            "execution_tool",
            "status_label",
            "last_run",
            "rows",
            "runtime_evidence",
        ]
    ].rename(
        columns={
            "flow_no": "#",
            "flow_name": "Data flow",
            "execution_tool": "Tool / runtime",
            "status_label": "Status",
            "last_run": "Last run",
            "rows": "Rows / units",
            "runtime_evidence": "Evidence shown",
        }
    )


def anomaly_chart() -> go.Figure:
    frame = pd.DataFrame(
        {
            "run": list(range(1, 11)),
            "rows": [142, 141, 143, 142, 144, 141, 142, 143, 141, 142],
        }
    )
    figure = go.Figure()
    figure.add_scatter(x=frame["run"], y=frame["rows"], mode="lines+markers", name="Rows")
    figure.add_hrect(y0=140, y1=144, fillcolor="rgba(15,118,110,0.08)", line_width=0)
    figure.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        font=dict(color="#1f2933"),
        xaxis_title="Recent runs",
        yaxis_title="Rows",
    )
    return figure


def reconciliation_table() -> pd.DataFrame:
    mode = stress_pulse_source_mode()
    status = "Pass" if mode == "live" else "Deferred"
    gold_value = "Live gold aggregate" if mode == "live" else "Pending aggregate contract"
    qbp_value = "Connected" if mode == "live" else "Not active in zero-risk build"
    return pd.DataFrame(
        [
            {
                "Metric": "Total assets",
                "Gold aggregate": gold_value,
                "FDIC QBP": qbp_value,
                "Status": status,
            },
            {
                "Metric": "Total deposits",
                "Gold aggregate": gold_value,
                "FDIC QBP": qbp_value,
                "Status": status,
            },
            {
                "Metric": "Total equity",
                "Gold aggregate": gold_value,
                "FDIC QBP": qbp_value,
                "Status": status,
            },
            {
                "Metric": "Net income",
                "Gold aggregate": gold_value,
                "FDIC QBP": qbp_value,
                "Status": status,
            },
        ]
    )


def freshness_table() -> pd.DataFrame:
    connector_report = load_state("connector_report", default={})
    sources = connector_report.get("sources", [])
    if not sources:
        return pd.DataFrame(
            [{"Source": "No connector report", "Freshness": "—", "SLA": "—", "Status": "Missing"}]
        )
    return pd.DataFrame(
        [
            {
                "Source": item["label"],
                "Freshness": "Configured" if item["ready"] else "Missing connector",
                "SLA": item["cadence"],
                "Status": item["status"],
            }
            for item in sources
            if item["enabled"]
        ]
    )


def _tool_status(*, configured: bool, scaffolded: bool = True) -> str:
    if configured:
        return "Configured"
    if scaffolded:
        return "Scaffolded"
    return "Not ready"


def platform_stack_frame() -> pd.DataFrame:
    settings = get_settings()
    return pd.DataFrame(
        [
            {
                "Component": "AWS S3 bronze mirror",
                "Role": "Raw landing and durable artifact storage",
                "Status": _tool_status(
                    configured=bool(
                        settings.aws_s3_mirror_enabled
                        and settings.aws_access_key_id
                        and settings.aws_secret_access_key
                    )
                ),
                "Readiness note": (
                    "Buckets: "
                    f"raw={settings.aws_s3_raw_bucket}, "
                    f"marts={settings.aws_s3_marts_bucket}"
                    if settings.aws_s3_mirror_enabled
                    else "Scaffolded in code, waiting for AWS credentials and bucket wiring"
                ),
            },
            {
                "Component": "Airflow orchestration",
                "Role": "Scheduled ingestion, transforms, and control-plane sync",
                "Status": _tool_status(
                    configured=Path(PROJECT_ROOT / "airflow" / "dags").exists()
                ),
                "Readiness note": "DAGs exist for FDIC, FRED, QBP, NIC, transforms, and sync",
            },
            {
                "Component": "dbt modeling",
                "Role": "Silver and gold transformations",
                "Status": _tool_status(
                    configured=Path(PROJECT_ROOT / "dbt" / "models").exists()
                ),
                "Readiness note": (
                    "Staging and mart models are scaffolded for resilient MVP sources"
                ),
            },
            {
                "Component": "Terraform infra",
                "Role": "Provision buckets, IAM, and deployment infrastructure",
                "Status": _tool_status(
                    configured=Path(PROJECT_ROOT / "terraform").exists()
                ),
                "Readiness note": "Terraform folder is present and reserved for infra rollout",
            },
            {
                "Component": "Snowflake warehouse",
                "Role": "Resume-grade analytical warehouse target",
                "Status": _tool_status(
                    configured=bool(
                        settings.snowflake_account
                        and settings.snowflake_user
                        and settings.snowflake_password
                    )
                ),
                "Readiness note": (
                    f"Role {settings.snowflake_role}, marts DB {settings.snowflake_database_marts}"
                    if settings.snowflake_account
                    else "Contract and env vars are scaffolded, waiting for account credentials"
                ),
            },
            {
                "Component": "FastAPI service",
                "Role": "Health, telemetry, and machine-facing endpoints",
                "Status": _tool_status(configured=True),
                "Readiness note": (
                    settings.finlens_api_base_url
                    or "Local-only until public API URL is set"
                ),
            },
            {
                "Component": "Cloudflare edge",
                "Role": "Domain, Turnstile, and public-edge controls",
                "Status": _tool_status(
                    configured=bool(
                        settings.cloudflare_zone_id
                        or settings.cloudflare_turnstile_site_key
                        or settings.cloudflare_api_token
                    )
                ),
                "Readiness note": (
                    f"Zone {settings.cloudflare_zone_id}"
                    if settings.cloudflare_zone_id
                    else "Ready to wire once zone, token, and Turnstile values are supplied"
                ),
            },
            {
                "Component": "Postgres control sync",
                "Role": "Telemetry and control-plane snapshot sync back home",
                "Status": _tool_status(configured=bool(settings.postgres_sync_dsn)),
                "Readiness note": (
                    f"Schema {settings.postgres_sync_schema}"
                    if settings.postgres_sync_dsn
                    else "Sync script is ready and waiting for POSTGRES_SYNC_DSN"
                ),
            },
        ]
    )


def tool_evidence_frame() -> pd.DataFrame:
    settings = get_settings()
    return pd.DataFrame(
        [
            {
                "Platform component": "Apache Airflow",
                "Operating role": (
                    "FDIC/FRED ingestion DAGs, source refresh ordering, retry boundaries"
                ),
                "Current state": "DAG definitions are present; scheduler runtime is not active yet",
                "Next operational signal": (
                    "Latest DAG run id, start time, duration, and task-level status"
                ),
            },
            {
                "Platform component": "dbt",
                "Operating role": "Staging, intermediate, and mart builds",
                "Current state": (
                    "Model files are present; local gold outputs are serving the app"
                ),
                "Next operational signal": (
                    "Run dbt build and expose model count, pass/fail tests, build duration"
                ),
            },
            {
                "Platform component": "Snowflake",
                "Operating role": "Raw/staging/intermediate/marts warehouse objects",
                "Current state": (
                    f"Configured account {settings.snowflake_account}"
                    if settings.snowflake_account
                    else "Credentials not supplied to this runtime"
                ),
                "Next operational signal": (
                    "Query INFORMATION_SCHEMA for table counts, row counts, and last altered time"
                ),
            },
        ]
    )


def service_endpoints_frame() -> pd.DataFrame:
    settings = get_settings()
    base = settings.finlens_api_base_url or "http://127.0.0.1:8010"
    public = settings.finlens_public_base_url or "http://127.0.0.1:8501"
    return pd.DataFrame(
        [
            {
                "Endpoint": "/health",
                "Served by": "FastAPI",
                "Purpose": "Structured service and connector health payload",
                "Path": f"{base}/health",
            },
            {
                "Endpoint": "/healthz",
                "Served by": "FastAPI",
                "Purpose": "Machine-facing uptime check for Uptime Kuma",
                "Path": f"{base}/healthz",
            },
            {
                "Endpoint": "/telemetry/events",
                "Served by": "FastAPI",
                "Purpose": "Receives interaction events and optional Turnstile validation",
                "Path": f"{base}/telemetry/events",
            },
            {
                "Endpoint": "/telemetry/summary",
                "Served by": "FastAPI",
                "Purpose": "Returns the current event summary",
                "Path": f"{base}/telemetry/summary",
            },
            {
                "Endpoint": "Streamlit app",
                "Served by": "Streamlit",
                "Purpose": "Business and technical presentation surface",
                "Path": public,
            },
        ]
    )


def control_sync_frame() -> pd.DataFrame:
    settings = get_settings()
    sync_state = load_state("postgres_sync_state", default={})
    telemetry = telemetry_summary()
    return pd.DataFrame(
        [
            {
                "Channel": "Telemetry events",
                "Destination": "Home Postgres",
                "Status": "Configured" if settings.postgres_sync_dsn else "Waiting on DSN",
                "Detail": (
                    f"{telemetry['event_count']} local events, "
                    f"{len(sync_state.get('telemetry_event_ids', []))} already synced"
                ),
            },
            {
                "Channel": "Connector report snapshots",
                "Destination": "Home Postgres",
                "Status": "Configured" if settings.postgres_sync_dsn else "Waiting on DSN",
                "Detail": f"Target schema: {settings.postgres_sync_schema}",
            },
            {
                "Channel": "Pipeline status snapshots",
                "Destination": "Home Postgres",
                "Status": "Configured" if settings.postgres_sync_dsn else "Waiting on DSN",
                "Detail": "Sync script persists pipeline, connector, and telemetry summaries",
            },
        ]
    )


def architecture_components_frame() -> pd.DataFrame:
    settings = get_settings()
    return pd.DataFrame(
        [
            {
                "Layer": "Edge and domain",
                "Primary component": "Cloudflare + custom domain",
                "Runtime": "Public edge",
                "Current posture": settings.project_domain,
            },
            {
                "Layer": "Presentation",
                "Primary component": "Streamlit",
                "Runtime": "App container / local runtime",
                "Current posture": "Business and technical surfaces are active",
            },
            {
                "Layer": "Service endpoints",
                "Primary component": "FastAPI",
                "Runtime": "API process",
                "Current posture": "Health and telemetry routes are implemented",
            },
            {
                "Layer": "Orchestration",
                "Primary component": "Airflow",
                "Runtime": "Scheduler / worker tier",
                "Current posture": "DAGs are scaffolded and ready for deployment wiring",
            },
            {
                "Layer": "Raw storage",
                "Primary component": "AWS S3",
                "Runtime": "Cloud object storage",
                "Current posture": (
                    "Mirror buckets declared under "
                    f"{settings.aws_default_region or 'pending region'}"
                ),
            },
            {
                "Layer": "Transforms",
                "Primary component": "dbt",
                "Runtime": "Transform runner",
                "Current posture": "Staging and mart models exist for MVP sources",
            },
            {
                "Layer": "Warehouse",
                "Primary component": "Snowflake",
                "Runtime": "Cloud warehouse",
                "Current posture": settings.snowflake_account or "Pending account values",
            },
            {
                "Layer": "Home control sync",
                "Primary component": "Postgres",
                "Runtime": "Home database",
                "Current posture": settings.postgres_sync_schema,
            },
        ]
    )


st.set_page_config(
    page_title="FinLens | Technical Surface",
    layout="wide",
    initial_sidebar_state="collapsed",
)
ensure_theme_state()
inject_styles(app_css(get_theme_mode(), sidebar_open=False))
top_navigation("hood", TECHNICAL_PAGE)
record_page_view("control_room", TECHNICAL_PAGE)
status_ribbon("Technical systems view")
active_section = get_technical_section()
intro_title = "Architecture Decisions" if active_section == "decisions" else "Control Room"
intro_copy = (
    "Internal data architecture handbook for the platform stack, source contracts, modeling "
    "standards, warehouse design, and activation path."
    if active_section == "decisions"
    else "This is the engineering proof surface: source freshness, reconciliation, quality "
    "posture, and the rule that dashboards read only from the gold layer."
)
page_intro(
    "Technical Surface",
    intro_title,
    intro_copy,
)

pipeline_frame = pipeline_status_frame()
settings = get_settings()

if active_section == "pipeline":
    card1, card2, card3, card4 = st.columns(4)
    with card1:
        metric_card(
            "FDIC BankFind",
            pipeline_frame.iloc[0]["status"],
            pipeline_frame.iloc[0]["note"],
        )
    with card2:
        metric_card("FRED", pipeline_frame.iloc[2]["status"], pipeline_frame.iloc[2]["note"])
    with card3:
        metric_card("Gold Marts", pipeline_frame.iloc[5]["status"], pipeline_frame.iloc[5]["note"])
    with card4:
        metric_card(
            "Dashboards",
            pipeline_frame.iloc[6]["status"],
            pipeline_frame.iloc[6]["note"],
        )
    infra1, infra2, infra3, infra4 = st.columns(4)
    stack = platform_stack_frame()
    with infra1:
        metric_card("AWS S3", stack.iloc[0]["Status"], "Bronze mirror readiness")
    with infra2:
        metric_card("Airflow", stack.iloc[1]["Status"], "DAG orchestration scaffold")
    with infra3:
        metric_card("dbt", stack.iloc[2]["Status"], "Silver and gold models")
    with infra4:
        metric_card("Snowflake", stack.iloc[4]["Status"], "Warehouse contract readiness")
    section_heading(
        "Core Data Engineering Stack",
        "This section names the execution layer explicitly: Airflow schedules the work, dbt "
        "models and validates it, and Snowflake is the warehouse target for the activated path.",
    )
    styled_table(tool_evidence_frame())
    section_heading(
        "Live Pipeline Status",
        "Each row shows both the business data movement and the engineering runtime responsible "
        "for that movement. Deferred sources are marked separately from failed jobs.",
    )
    st.plotly_chart(dag_chart(pipeline_frame), width="stretch")
    styled_table(pipeline_status_table(pipeline_frame))
    section_heading(
        "Platform Stack Readiness",
        "Infrastructure readiness for the deployable platform: object storage, orchestration, "
        "transforms, warehouse, API service, edge routing, and control-plane sync.",
    )
    styled_table(platform_stack_frame())
    tech_bulletin(
        "Health endpoint",
        "/healthz is the machine-facing endpoint intended for Uptime Kuma.",
    )

elif active_section == "status":
    section_heading(
        "Reconciliation (dbt Data Quality)",
        "This is the credibility panel. In the fully activated warehouse path, these checks belong "
        "in dbt tests and marts-level reconciliation output.",
    )
    styled_table(reconciliation_table())
    left, right = st.columns(2)
    with left:
        section_heading(
            "Service Endpoints",
            "These are the machine-facing endpoints and public surfaces currently wired for the "
            "stack.",
        )
        styled_table(service_endpoints_frame())
    with right:
        section_heading(
            "Control Sync (Postgres)",
            "Telemetry and control-plane snapshots can sync back to home Postgres once the DSN "
            "is supplied.",
        )
        styled_table(control_sync_frame())

elif active_section == "implementation":
    section_heading(
        "Data Quality (Airflow + dbt)",
        "Operational quality checks are grouped by the platform component expected to produce "
        "them: Airflow for freshness, dbt for tests, and Snowflake for warehouse observability.",
    )
    styled_table(tool_evidence_frame())
    section_heading(
        "Source Freshness (Airflow Inputs)",
        "These are the active source contracts that Airflow should refresh when the scheduler is "
        "enabled.",
    )
    styled_table(freshness_table())
    section_heading(
        "Warehouse Activation Checklist (Snowflake + dbt)",
        "These are the concrete checks needed before claiming the full warehouse path is live.",
    )
    activation = pd.DataFrame(
        [
            {
                "Layer": "Snowflake connection",
                "Required proof": "Successful SELECT CURRENT_ACCOUNT(), CURRENT_ROLE()",
                "Status": "Configured" if settings.snowflake_account else "Pending",
            },
            {
                "Layer": "dbt build",
                "Required proof": "dbt build exits cleanly with model and test counts",
                "Status": "Ready to run",
            },
            {
                "Layer": "Airflow DAG",
                "Required proof": "Latest DAG run status, duration, and task-level state",
                "Status": "DAG scaffold present",
            },
        ]
    )
    styled_table(activation)

elif active_section == "decisions":
    render_architecture_decisions()
