# ruff: noqa: E402,E501

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
from finlens.evidence import (
    airflow_run_rows,
    dbt_artifact_summary,
    dbt_result_rows,
    source_landing_rows,
    warehouse_table_names,
    warehouse_table_preview,
    warehouse_table_rows,
)
from finlens.pipeline_runs import latest_pipeline_run
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
        "Not Activated": "rgba(180, 170, 156, 0.35)",
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
                    "QBP",
                    "FRED",
                    "NIC",
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
        "Not Activated": "⚪ Not Activated",
    }
    tool_map = {
        "FDIC -> Bronze": "Airflow task + Python extractor",
        "QBP -> Bronze": "Airflow task + FDIC summary extractor",
        "FRED -> Bronze": "Airflow task + FRED extractor",
        "NIC -> Bronze": "Airflow task + institution metadata extractor",
        "Bronze -> Silver": "dbt staging / canonical model",
        "Silver -> Gold": "dbt mart build",
        "Gold -> Dashboards": "Snowflake/DuckDB mart read + Streamlit",
    }
    evidence_map = {
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
    gold_value = "Live gold aggregate" if mode == "live" else "QBP aggregate not activated"
    qbp_value = "Connected" if mode == "live" else "No QBP source URL configured"
    detail = (
        "Validated against QBP aggregate contract"
        if mode == "live"
        else "Disabled rather than faked; activate FDIC_QBP_SOURCE_URL to reconcile"
    )
    return pd.DataFrame(
        [
            {
                "Metric": "Total assets",
                "Gold aggregate": gold_value,
                "FDIC QBP": qbp_value,
                "Status": status,
                "Evidence": detail,
            },
            {
                "Metric": "Total deposits",
                "Gold aggregate": gold_value,
                "FDIC QBP": qbp_value,
                "Status": status,
                "Evidence": detail,
            },
            {
                "Metric": "Total equity",
                "Gold aggregate": gold_value,
                "FDIC QBP": qbp_value,
                "Status": status,
                "Evidence": detail,
            },
            {
                "Metric": "Net income",
                "Gold aggregate": gold_value,
                "FDIC QBP": qbp_value,
                "Status": status,
                "Evidence": detail,
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
                "Freshness": "Success" if item["ready"] else "Not Activated",
                "SLA": item["cadence"],
                "Status": item["status"],
                "Required input": ", ".join(item.get("required_env", [])) or "None",
                "Missing input": ", ".join(item.get("missing_env", [])) or "None",
            }
            for item in sources
        ]
    )


def source_activation_frame() -> pd.DataFrame:
    connector_report = load_state("connector_report", default={})
    sources = connector_report.get("sources", []) if isinstance(connector_report, dict) else []
    if not sources:
        return pd.DataFrame(
            [
                {
                    "Source": "No connector report",
                    "Activation": "Missing",
                    "Reason": "Run connector readiness",
                    "Cadence": "—",
                }
            ]
        )
    rows = []
    for item in sources:
        missing = item.get("missing_env", [])
        if item.get("ready"):
            activation = "Active"
            reason = "Connector inputs present and runtime check passed"
        elif item.get("enabled"):
            activation = "Blocked"
            reason = f"Missing: {', '.join(missing)}" if missing else "Connector not ready"
        else:
            activation = "Not Activated"
            reason = (
                f"Inactive source contract; missing {', '.join(missing)}"
                if missing
                else "Inactive source contract"
            )
        rows.append(
            {
                "Source": item["label"],
                "Activation": activation,
                "Reason": reason,
                "Cadence": item["cadence"],
            }
        )
    return pd.DataFrame(rows)


def _success_status(status: str | None) -> str:
    if status in {"Ready", "Success", "Pass"}:
        return "Success"
    if status in {"Failed", "Unavailable", "Missing"}:
        return "Failed"
    if status in {"Scaffolded", "Deferred"}:
        return str(status)
    return "Pending"


def _probe_status(probes: dict, key: str, fallback: str = "Pending") -> str:
    payload = probes.get(key, {}) if isinstance(probes, dict) else {}
    status = payload.get("status")
    runtime_status = payload.get("runtime_status")
    if runtime_status == "Ready":
        return "Success"
    if status:
        return _success_status(str(status))
    return fallback


def _probe_detail(probes: dict, key: str, fallback: str) -> str:
    payload = probes.get(key, {}) if isinstance(probes, dict) else {}
    detail = payload.get("detail")
    if detail:
        return str(detail)
    return fallback


def _tool_status(*, configured: bool, scaffolded: bool = True) -> str:
    if configured:
        return "Success"
    if scaffolded:
        return "Scaffolded"
    return "Not ready"


def platform_stack_frame() -> pd.DataFrame:
    settings = get_settings()
    probes = load_state("platform_probe_report", default={})
    return pd.DataFrame(
        [
            {
                "Component": "AWS S3 bronze mirror",
                "Role": "Raw landing and durable artifact storage",
                "Status": _probe_status(
                    probes,
                    "s3",
                    _tool_status(
                        configured=bool(
                            settings.aws_s3_mirror_enabled
                            and settings.aws_access_key_id
                            and settings.aws_secret_access_key
                        )
                    ),
                ),
                "Readiness note": _probe_detail(
                    probes,
                    "s3",
                    (
                        "Buckets: "
                        f"raw={settings.aws_s3_raw_bucket}, "
                        f"marts={settings.aws_s3_marts_bucket}"
                        if settings.aws_s3_mirror_enabled
                        else "Scaffolded in code, waiting for AWS credentials and bucket wiring"
                    ),
                ),
            },
            {
                "Component": "Airflow orchestration",
                "Role": "Scheduled ingestion, transforms, and control-plane sync",
                "Status": _probe_status(
                    probes,
                    "airflow",
                    _tool_status(configured=Path(PROJECT_ROOT / "airflow" / "dags").exists()),
                ),
                "Readiness note": _probe_detail(
                    probes,
                    "airflow",
                    "DAGs exist for FDIC, FRED, QBP, NIC, transforms, and sync",
                ),
            },
            {
                "Component": "dbt modeling",
                "Role": "Silver and gold transformations",
                "Status": _probe_status(
                    probes,
                    "dbt",
                    _tool_status(configured=Path(PROJECT_ROOT / "dbt" / "models").exists()),
                ),
                "Readiness note": _probe_detail(
                    probes,
                    "dbt",
                    "Staging and mart models are scaffolded for resilient MVP sources",
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
                "Status": _probe_status(
                    probes,
                    "snowflake",
                    _tool_status(
                        configured=bool(
                            settings.snowflake_account
                            and settings.snowflake_user
                            and settings.snowflake_password
                        )
                    ),
                ),
                "Readiness note": _probe_detail(
                    probes,
                    "snowflake",
                    (
                        f"Role {settings.snowflake_role}, "
                        f"marts DB {settings.snowflake_database_marts}"
                        if settings.snowflake_account
                        else "Contract and env vars are scaffolded, waiting for account credentials"
                    ),
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
                "Status": _probe_status(
                    probes,
                    "postgres",
                    _tool_status(configured=bool(settings.postgres_sync_dsn)),
                ),
                "Readiness note": _probe_detail(
                    probes,
                    "postgres",
                    (
                        f"Schema {settings.postgres_sync_schema}"
                        if settings.postgres_sync_dsn
                        else "Sync script is ready and waiting for POSTGRES_SYNC_DSN"
                    ),
                ),
            },
        ]
    )


def tool_evidence_frame() -> pd.DataFrame:
    settings = get_settings()
    probes = load_state("platform_probe_report", default={})
    dbt_report = load_state("dbt_build_report", default={})
    latest_run = latest_pipeline_run()
    latest_run_label = latest_run.get("run_id", "No run recorded")

    def probe_detail(key: str, fallback: str) -> str:
        payload = probes.get(key, {}) if isinstance(probes, dict) else {}
        status = payload.get("status")
        detail = payload.get("detail")
        if status and detail:
            return f"{status}: {detail}"
        if status:
            return str(status)
        return fallback

    return pd.DataFrame(
        [
            {
                "Platform component": "Apache Airflow",
                "Operating role": (
                    "FDIC/FRED ingestion DAGs, source refresh ordering, retry boundaries"
                ),
                "Current state": probe_detail(
                    "airflow",
                    "DAG definitions are present; scheduler runtime is not active yet",
                ),
                "Next operational signal": (
                    "Latest DAG run id, start time, duration, and task-level status"
                ),
            },
            {
                "Platform component": "dbt",
                "Operating role": "Staging, intermediate, and mart builds",
                "Current state": (
                    f"{dbt_report.get('status')} build on {dbt_report.get('target')} "
                    f"at {dbt_report.get('captured_at')}"
                    if dbt_report
                    else probe_detail(
                        "dbt",
                        "Model files are present; local gold outputs are serving the app",
                    )
                ),
                "Next operational signal": (
                    "Run dbt build and expose model count, pass/fail tests, build duration"
                ),
            },
            {
                "Platform component": "Snowflake",
                "Operating role": "Raw/staging/intermediate/marts warehouse objects",
                "Current state": probe_detail(
                    "snowflake",
                    f"Configured account {settings.snowflake_account}"
                    if settings.snowflake_account
                    else "Credentials not supplied to this runtime",
                ),
                "Next operational signal": (
                    "Query INFORMATION_SCHEMA for table counts, row counts, and last altered time"
                ),
            },
            {
                "Platform component": "Pipeline run ledger",
                "Operating role": "Durable execution summary for the technical surface",
                "Current state": latest_run_label,
                "Next operational signal": "Run scripts/run_local_pipeline.py --probe-platform",
            },
        ]
    )


def latest_pipeline_run_frame() -> pd.DataFrame:
    latest_run = latest_pipeline_run()
    if not latest_run:
        return pd.DataFrame(
            [
                {
                    "Step": "No run recorded",
                    "Status": "Pending",
                    "Duration": "—",
                    "Detail": "Run scripts/run_local_pipeline.py --probe-platform",
                }
            ]
        )
    rows = []
    for step in latest_run.get("steps", []):
        rows.append(
            {
                "Step": step.get("name"),
                "Status": step.get("status"),
                "Duration": f"{step.get('duration_seconds', 0)}s",
                "Detail": step.get("detail"),
            }
        )
    return pd.DataFrame(rows)


def dbt_build_frame() -> pd.DataFrame:
    report = load_state("dbt_build_report", default={})
    if not report:
        return pd.DataFrame(
            [
                {
                    "Target": "local",
                    "Status": "Pending",
                    "Return code": "—",
                    "Captured at": "—",
                    "Summary": "Run scripts/run_local_pipeline.py --run-dbt-build",
                }
            ]
        )
    stdout = str(report.get("stdout_tail", ""))
    summary_line = next(
        (
            line.strip()
            for line in reversed(stdout.splitlines())
            if line.strip().startswith("Done.")
        ),
        report.get("status", "Unknown"),
    )
    return pd.DataFrame(
        [
            {
                "Target": report.get("target"),
                "Status": report.get("status"),
                "Return code": report.get("returncode"),
                "Captured at": report.get("captured_at"),
                "Summary": summary_line,
            }
        ]
    )


def dbt_quality_summary_frame() -> pd.DataFrame:
    summary = dbt_artifact_summary()
    return pd.DataFrame(
        [
            {
                "Build status": summary["build_status"],
                "Target": summary["target"],
                "Models passed": summary["models_success"],
                "Tests passed": summary["tests_success"],
                "Failures": summary["failures"],
                "Total nodes": summary["total_nodes"],
                "Artifact available": "Yes" if summary["artifact_available"] else "No",
                "Captured at": summary["captured_at"],
            }
        ]
    )


def dbt_results_frame() -> pd.DataFrame:
    rows = dbt_result_rows()
    if not rows:
        return pd.DataFrame(
            [
                {
                    "Resource type": "No artifact",
                    "Name": "Run dbt build",
                    "Status": "Pending",
                    "Execution seconds": "—",
                    "Adapter response": "dbt target/run_results.json is not present",
                }
            ]
        )
    return pd.DataFrame(rows)


def warehouse_inventory_frame() -> pd.DataFrame:
    rows = warehouse_table_rows()
    if not rows:
        return pd.DataFrame(
            [
                {
                    "Layer": "No warehouse",
                    "Schema": "—",
                    "Table": "Run pipeline",
                    "Rows": "—",
                    "Columns": "—",
                }
            ]
        )
    return pd.DataFrame(rows)


def source_landing_frame() -> pd.DataFrame:
    rows = source_landing_rows()
    if not rows:
        return pd.DataFrame(
            [
                {
                    "Source": "No raw files",
                    "Raw files": 0,
                    "Latest artifact": "—",
                    "Latest record count": "—",
                    "Ingested at": "—",
                    "Storage path": "Run ingestion",
                }
            ]
        )
    return pd.DataFrame(rows)


def render_data_browser(stage_key: str = "pipeline") -> None:
    tables = warehouse_table_names()
    if not tables:
        tech_bulletin("Interactive Data Browser", "Run the pipeline to create browsable tables.")
        return
    section_heading(
        "Interactive Data Browser",
        "Read-only preview of the tables created by the pipeline. Use this to inspect the "
        "bronze/raw and gold/mart outputs without modifying warehouse data.",
    )
    stage_options = {
        "Bronze/raw": [table for table in tables if table.startswith("raw.")],
        "Gold marts": [table for table in tables if table.startswith("marts.")],
        "All tables": tables,
    }
    stage_options = {label: values for label, values in stage_options.items() if values}
    controls_left, controls_right = st.columns(2)
    with controls_left:
        stage = st.selectbox(
            "Pipeline stage",
            list(stage_options),
            key=f"{stage_key}_browser_stage",
        )
    available = stage_options[stage]
    with controls_right:
        table_ref = st.selectbox(
            "Table",
            available,
            key=f"{stage_key}_browser_table",
        )
    preview_total = warehouse_table_preview(table_ref, limit=1, offset=0)["total_rows"]
    page_size = 6
    total_pages = max(1, (preview_total + page_size - 1) // page_size)
    page_key = f"{stage_key}_browser_page"
    if st.session_state.get(page_key, 1) > total_pages:
        st.session_state[page_key] = total_pages
    if st.session_state.get(page_key, 1) < 1:
        st.session_state[page_key] = 1
    current_page = int(st.session_state.get(page_key, 1))
    preview = warehouse_table_preview(
        table_ref,
        limit=page_size,
        offset=(current_page - 1) * page_size,
    )
    st.caption(
        f"`{table_ref}` · showing rows {(current_page - 1) * page_size + 1:,}-"
        f"{(current_page - 1) * page_size + len(preview['rows']):,} of "
        f"{preview['total_rows']:,}"
    )
    styled_table(pd.DataFrame(preview["rows"], columns=preview["columns"]))
    _, pager, _ = st.columns([1.4, 2.2, 1.4])
    with pager:
        st.slider(
            "Page",
            min_value=1,
            max_value=total_pages,
            value=current_page,
            key=page_key,
        )


def airflow_runs_frame() -> pd.DataFrame:
    rows = airflow_run_rows()
    if not rows:
        return pd.DataFrame(
            [
                {
                    "DAG": "No run evidence",
                    "Latest run": "Run Airflow evidence collector",
                    "State": "Pending",
                    "Started": "—",
                    "Ended": "—",
                }
            ]
        )
    return pd.DataFrame(rows)


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
    probes = load_state("platform_probe_report", default={})
    sync_status = _probe_status(
        probes,
        "postgres",
        "Success" if settings.postgres_sync_dsn else "Waiting on DSN",
    )
    sync_state = load_state("postgres_sync_state", default={})
    telemetry = telemetry_summary()
    return pd.DataFrame(
        [
            {
                "Channel": "Telemetry events",
                "Destination": "Home Postgres",
                "Status": sync_status,
                "Detail": (
                    f"{telemetry['event_count']} local events, "
                    f"{len(sync_state.get('telemetry_event_ids', []))} already synced"
                ),
            },
            {
                "Channel": "Connector report snapshots",
                "Destination": "Home Postgres",
                "Status": sync_status,
                "Detail": f"Target schema: {settings.postgres_sync_schema}",
            },
            {
                "Channel": "Pipeline status snapshots",
                "Destination": "Home Postgres",
                "Status": sync_status,
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
        "Live Pipeline Status",
        "Real-time run status by flow. The chart shows the movement across sources, bronze, "
        "silver, gold, and dashboard serving; the table names the runtime responsible for each "
        "movement.",
    )
    st.plotly_chart(dag_chart(pipeline_frame), width="stretch")
    styled_table(pipeline_status_table(pipeline_frame))
    render_data_browser("pipeline")

    with st.expander("Core Data Engineering Stack", expanded=False):
        section_heading(
            "Tool Participation",
            "Airflow schedules the work, dbt models and validates it, Snowflake is the cloud "
            "warehouse target, and Streamlit/FastAPI serve the portfolio surface.",
        )
        styled_table(tool_evidence_frame())
        section_heading(
            "Platform Stack Readiness",
            "Infrastructure readiness for object storage, orchestration, transforms, warehouse, "
            "API service, edge routing, and control-plane sync.",
        )
        styled_table(platform_stack_frame())

    with st.expander("Source Evidence", expanded=False):
        section_heading(
            "Source Landing Evidence",
            "Raw landing files created by active connectors, including retained artifact count, "
            "latest source volume, ingest time, and storage path.",
        )
        styled_table(source_landing_frame())
        section_heading(
            "Source Activation Contract",
            "Active production sources are separated from inactive contracts so deferred scope is "
            "not confused with failed jobs.",
        )
        styled_table(source_activation_frame())

    with st.expander("Warehouse And Run Ledger", expanded=False):
        section_heading(
            "Warehouse Table Inventory",
            "DuckDB/Snowflake-parity warehouse objects currently serving the dashboard contract.",
        )
        styled_table(warehouse_inventory_frame())
        section_heading(
            "Latest Pipeline Run",
            "Execution ledger written by the pipeline runner, including step status and duration.",
        )
        styled_table(latest_pipeline_run_frame())

    with st.expander("Airflow And dbt Evidence", expanded=False):
        section_heading(
            "Airflow Run Evidence",
            "Latest DAG states captured from the Airflow runtime.",
        )
        styled_table(airflow_runs_frame())
        section_heading(
            "dbt Build Result",
            "Latest transformation run against the analytical warehouse target.",
        )
        styled_table(dbt_build_frame())
        section_heading(
            "dbt Data Quality Summary",
            "Counts parsed from dbt artifacts: models, tests, failures, and total executed nodes.",
        )
        styled_table(dbt_quality_summary_frame())
        section_heading(
            "dbt Node-Level Results",
            "Latest model and test outcomes from dbt artifacts.",
        )
        styled_table(dbt_results_frame())

elif active_section == "status":
    section_heading(
        "Reconciliation (dbt Data Quality)",
        "The current live path includes FDIC failures, FRED macro data, FDIC aggregate summary "
        "data, and active institution metadata.",
    )
    styled_table(reconciliation_table())
    section_heading(
        "dbt Data Quality Summary",
        "Latest dbt artifact metrics. Failures here would be the first reason not to trust a mart.",
    )
    styled_table(dbt_quality_summary_frame())
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
    probes = load_state("platform_probe_report", default={})
    section_heading(
        "Data Quality (Airflow + dbt)",
        "Operational quality checks are grouped by the platform component expected to produce "
        "them: Airflow for freshness, dbt for tests, and Snowflake for warehouse observability.",
    )
    styled_table(tool_evidence_frame())
    left, right = st.columns(2)
    with left:
        section_heading(
            "Airflow Run Evidence",
            "Scheduler-visible DAG runs and states.",
        )
        styled_table(airflow_runs_frame())
    with right:
        section_heading(
            "dbt Node-Level Results",
            "Model and test results parsed from dbt's generated artifacts.",
        )
        styled_table(dbt_results_frame())

    with st.expander("Source Freshness And Activation", expanded=False):
        section_heading(
            "Source Freshness (Airflow Inputs)",
            "Active source contracts Airflow refreshes when the scheduler runs.",
        )
        styled_table(freshness_table())
        section_heading(
            "Source Activation Contract",
            "Active connectors are separated from source contracts present in code but not "
            "activated in production.",
        )
        styled_table(source_activation_frame())

    section_heading(
        "Warehouse Activation Checklist (Snowflake + dbt)",
        "Concrete checks needed before claiming the full warehouse path is live.",
    )
    activation = pd.DataFrame(
        [
            {
                "Layer": "Snowflake connection",
                "Required proof": "Successful SELECT CURRENT_ACCOUNT(), CURRENT_ROLE()",
                "Status": _probe_status(
                    probes,
                    "snowflake",
                    "Success" if settings.snowflake_account else "Pending",
                ),
            },
            {
                "Layer": "dbt build",
                "Required proof": "dbt build exits cleanly with model and test counts",
                "Status": _probe_status(probes, "dbt", "Ready to run"),
            },
            {
                "Layer": "Airflow DAG",
                "Required proof": "Latest DAG run status, duration, and task-level state",
                "Status": _probe_status(probes, "airflow", "DAG scaffold present"),
            },
        ]
    )
    styled_table(activation)
    section_heading(
        "Transform Preview",
        "A compact before/after view of the central transform pattern: raw source payloads are "
        "loaded, normalized into typed warehouse tables, then exposed as Gold marts.",
    )
    example = pd.DataFrame(
        [
            {
                "Before": '{"Bank Name": "First-Citizens Bank & Trust Company", "Closing Date": "2023-03-10"}',
                "After": '{"bank_name": "First-Citizens Bank & Trust Company", "closing_date": "2023-03-10", "year": 2023}',
                "Rule": "Normalize column names, parse dates, preserve source values",
            }
        ]
    )
    styled_table(example)

elif active_section == "decisions":
    render_architecture_decisions()
