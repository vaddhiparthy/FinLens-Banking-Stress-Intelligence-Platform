# ruff: noqa: E501

from __future__ import annotations

import pandas as pd
import streamlit as st

from streamlit_app.lib.ui_components import section_heading, tech_bulletin

REFERENCE_LINKS = {
    "AWS S3": "https://aws.amazon.com/documentation-overview/s3/",
    "Airflow": "https://airflow.apache.org/docs/index.html",
    "dbt": "https://docs.getdbt.com/",
    "Terraform": "https://developer.hashicorp.com/terraform/registry/providers",
    "Terraform AWS Provider": "https://registry.terraform.io/providers/hashicorp/aws/latest/docs",
    "Snowflake": "https://docs.snowflake.com/en/",
    "Streamlit": "https://docs.streamlit.io/",
    "FastAPI": "https://fastapi.org/",
}


def _match(query: str, *values: str) -> bool:
    if not query:
        return True
    haystack = " ".join(values).lower()
    return query.lower() in haystack


def _flow_html() -> str:
    return """
    <div class="arch-flow">
        <div class="arch-node">Source Contracts<br><span>FDIC, FRED, QBP, NIC</span></div>
        <div class="arch-arrow">-></div>
        <div class="arch-node">Bronze Zone<br><span>Immutable raw snapshots in local/S3 storage</span></div>
        <div class="arch-arrow">-></div>
        <div class="arch-node">Silver Zone<br><span>Canonical entities, dates, and source contracts</span></div>
        <div class="arch-arrow">-></div>
        <div class="arch-node">Gold Marts<br><span>Business-ready facts for dashboard consumption</span></div>
        <div class="arch-arrow">-></div>
        <div class="arch-node">Serving Layer<br><span>Streamlit reads Gold; FastAPI reports health</span></div>
    </div>
    <style>
    .arch-flow {
        display: grid;
        grid-template-columns: 1fr auto 1fr auto 1fr auto 1fr auto 1fr;
        gap: .65rem;
        align-items: stretch;
        margin: .6rem 0 1rem 0;
    }
    .arch-node {
        border: 1px solid rgba(42, 55, 70, .18);
        background: rgba(255, 252, 246, .72);
        border-radius: 10px;
        padding: .78rem .85rem;
        color: #1f2933;
        font-weight: 800;
        min-height: 5rem;
        box-shadow: 0 10px 25px rgba(31, 41, 51, .07);
    }
    .arch-node span {
        display: block;
        margin-top: .28rem;
        color: #6a6b74;
        font-weight: 500;
        line-height: 1.35;
        font-size: .82rem;
    }
    .arch-arrow {
        display: flex;
        align-items: center;
        justify-content: center;
        color: #7f6b58;
        font-weight: 900;
    }
    @media (max-width: 1100px) {
        .arch-flow { grid-template-columns: 1fr; }
        .arch-arrow { transform: rotate(90deg); min-height: 1rem; }
    }
    </style>
    """


def _component_catalog() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Component": "AWS S3",
                "Architecture role": "Bronze object store and replay boundary",
                "Data architect view": "Stores raw source artifacts by source and ingest date before warehouse loading.",
                "Activation status": "Waiting on AWS credentials/buckets",
            },
            {
                "Component": "Airflow",
                "Architecture role": "Orchestration plane",
                "Data architect view": "Owns run order, dependencies, retry posture, and scheduled movement across layers.",
                "Activation status": "DAGs scaffolded",
            },
            {
                "Component": "dbt",
                "Architecture role": "Transformation and semantic contract layer",
                "Data architect view": "Defines staging, intermediate, and mart SQL models plus tests and lineage.",
                "Activation status": "Models scaffolded",
            },
            {
                "Component": "Snowflake",
                "Architecture role": "Analytical warehouse target",
                "Data architect view": "Houses raw, staging, intermediate, and marts databases with separate warehouses.",
                "Activation status": "Waiting on Snowflake credentials",
            },
            {
                "Component": "Terraform",
                "Architecture role": "Infrastructure-as-code boundary",
                "Data architect view": "Codifies cloud resources so storage and warehouse dependencies are reproducible.",
                "Activation status": "Modules scaffolded",
            },
            {
                "Component": "Great Expectations",
                "Architecture role": "Data quality checkpoint layer",
                "Data architect view": "Reserved for load and serve quality checks where dbt tests are not expressive enough.",
                "Activation status": "Scaffolded, not on the critical path",
            },
            {
                "Component": "DuckDB",
                "Architecture role": "Local analytical runtime",
                "Data architect view": "Keeps the product runnable and testable before Snowflake credentials are available.",
                "Activation status": "Active locally",
            },
            {
                "Component": "FastAPI",
                "Architecture role": "Machine-facing control interface",
                "Data architect view": "Publishes health and telemetry endpoints consumed by monitoring or sync jobs.",
                "Activation status": "Active",
            },
            {
                "Component": "Streamlit",
                "Architecture role": "Presentation layer",
                "Data architect view": "Reads Gold outputs and renders the business and technical surfaces.",
                "Activation status": "Active",
            },
        ]
    )


def _source_contracts() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Source": "FDIC BankFind failures",
                "Grain": "One row per failed institution event",
                "Landing contract": "Bronze JSON snapshot",
                "Gold usage": "Failure timeline, failure table, failure counts",
            },
            {
                "Source": "FRED series batch",
                "Grain": "One observation per series/date",
                "Landing contract": "Bronze observations by series id",
                "Gold usage": "Macro Transmission indicators and lag matrix",
            },
            {
                "Source": "FDIC QBP normalized artifact",
                "Grain": "One industry aggregate row per quarter",
                "Landing contract": "Normalized CSV/JSON with the Stress Pulse contract",
                "Gold usage": "Net income, ROA, NIM, problem banks, loss series",
            },
            {
                "Source": "NIC current parent metadata",
                "Grain": "One current institution-to-parent relationship row",
                "Landing contract": "Current-parent artifact only",
                "Gold usage": "Institution context when connected",
            },
        ]
    )


def _warehouse_layers() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Layer": "Bronze",
                "Primary concern": "Source fidelity",
                "Typical object": "Raw JSON/CSV artifact with ingest metadata",
                "Owned by": "Ingestion + S3 landing pattern",
            },
            {
                "Layer": "Silver",
                "Primary concern": "Canonical normalization",
                "Typical object": "Typed staging tables with standard names and date keys",
                "Owned by": "dbt staging models",
            },
            {
                "Layer": "Intermediate",
                "Primary concern": "Reusable business shaping",
                "Typical object": "Joined, conformed, or enriched views",
                "Owned by": "dbt intermediate models",
            },
            {
                "Layer": "Gold",
                "Primary concern": "Stable consumption contract",
                "Typical object": "Fact/mart table used directly by Streamlit",
                "Owned by": "dbt marts + local warehouse fallback",
            },
        ]
    )


def _dbt_model_catalog() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Model": "stg_fdic_failed_banks",
                "Layer": "Staging",
                "Purpose": "Normalize FDIC failed-bank event records.",
            },
            {
                "Model": "stg_fred_observations",
                "Layer": "Staging",
                "Purpose": "Normalize macro observations by series/date.",
            },
            {
                "Model": "stg_fdic_qbp",
                "Layer": "Staging",
                "Purpose": "Normalize the quarterly industry aggregate contract.",
            },
            {
                "Model": "stg_nic_current_parent",
                "Layer": "Staging",
                "Purpose": "Normalize current parent metadata without historical lineage complexity.",
            },
            {
                "Model": "fct_bank_failures",
                "Layer": "Marts",
                "Purpose": "Serve Failure Forensics.",
            },
            {
                "Model": "fct_financial_metrics",
                "Layer": "Marts",
                "Purpose": "Serve Macro Transmission.",
            },
            {
                "Model": "fct_stress_pulse",
                "Layer": "Marts",
                "Purpose": "Serve Stress Pulse.",
            },
        ]
    )


def _decision_register() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Decision": "Dashboard reads Gold only",
                "Rationale": "Protects the UI from source volatility and schema drift.",
                "Data impact": "All business-facing metrics must pass through a modeled contract.",
            },
            {
                "Decision": "S3 is the bronze system of record when activated",
                "Rationale": "Raw files need an external replay and audit boundary.",
                "Data impact": "Warehouse rebuilds can start from retained source artifacts.",
            },
            {
                "Decision": "Airflow owns run order, not business logic",
                "Rationale": "Orchestration should sequence work, not hide transformation rules.",
                "Data impact": "Transform definitions remain inspectable in dbt and Python contracts.",
            },
            {
                "Decision": "dbt owns warehouse transformations",
                "Rationale": "SQL model contracts are easier to review, test, and discuss in interviews.",
                "Data impact": "Silver and Gold lineage becomes explicit.",
            },
            {
                "Decision": "Snowflake is credential-gated",
                "Rationale": "The project should not pretend to be using paid infrastructure before keys exist.",
                "Data impact": "Local DuckDB keeps the product runnable until the warehouse is turned on.",
            },
            {
                "Decision": "SEC, UBPR, FR Y-9C, and SLOOS are outside active scope",
                "Rationale": "Those feeds add semantic, access, or maintenance burden beyond current value.",
                "Data impact": "The active source set stays durable and explainable.",
            },
        ]
    )


def _glossary() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Term": "Data contract",
                "Meaning": "A stable agreement about grain, columns, data types, and meaning.",
            },
            {
                "Term": "Grain",
                "Meaning": "The level at which one row represents one business fact.",
            },
            {
                "Term": "Bronze",
                "Meaning": "The raw landing layer that preserves source evidence.",
            },
            {
                "Term": "Silver",
                "Meaning": "The normalized layer where source payloads become canonical tables.",
            },
            {
                "Term": "Gold",
                "Meaning": "The consumption layer built for stable reporting and application use.",
            },
            {
                "Term": "Mart",
                "Meaning": "A business-ready table or view designed around a specific analytical surface.",
            },
            {
                "Term": "Lineage",
                "Meaning": "The path from source artifact through transformations to final business output.",
            },
            {
                "Term": "Idempotency",
                "Meaning": "A pipeline property where rerunning a step produces the same intended result.",
            },
            {
                "Term": "Warehouse",
                "Meaning": "The analytical storage and compute layer where modeled data is queried.",
            },
            {
                "Term": "Semantic layer",
                "Meaning": "The modeled business meaning exposed to consumers, independent of raw source shape.",
            },
        ]
    )


def _external_references() -> pd.DataFrame:
    return pd.DataFrame(
        [{"Topic": name, "Official reference": url} for name, url in REFERENCE_LINKS.items()]
    )


def _render_filtered_table(frame: pd.DataFrame, query: str) -> None:
    if query:
        mask = frame.apply(
            lambda row: query.lower() in " ".join(map(str, row.values)).lower(),
            axis=1,
        )
        frame = frame[mask]
    st.dataframe(frame, width="stretch", hide_index=True)


def _render_platform(query: str) -> None:
    if _match(query, "platform architecture data stack"):
        section_heading(
            "Data Platform Architecture",
            "FinLens is organized as a governed analytical pipeline: official public sources land "
            "into raw storage, dbt-modelable structures produce Silver and Gold contracts, and the "
            "presentation layer consumes only those Gold outputs.",
        )
        st.markdown(_flow_html(), unsafe_allow_html=True)
        tech_bulletin(
            "Architecture posture",
            "The business UI is intentionally small. The engineering story is the platform beneath it: "
            "S3 landing, Airflow scheduling, dbt modeling, Snowflake warehouse targeting, and a clear "
            "contract boundary between data production and data consumption.",
        )

    if _match(query, "component catalog"):
        section_heading(
            "Component Catalog",
            "This catalog describes each tool by its data-architecture responsibility, not by vendor name.",
        )
        _render_filtered_table(_component_catalog(), query)


def _render_data_modeling(query: str) -> None:
    if _match(query, "source contracts grain"):
        section_heading(
            "Source Contracts And Grain",
            "Every source is documented by row grain before it is allowed to feed a dashboard. This "
            "prevents accidental joins, ambiguous aggregations, and source-specific leakage into the UI.",
        )
        _render_filtered_table(_source_contracts(), query)

    if _match(query, "warehouse layers bronze silver gold"):
        section_heading(
            "Warehouse Layering Standard",
            "The same conceptual model applies locally and in Snowflake. DuckDB keeps development "
            "runnable, while Snowflake becomes the enterprise warehouse target once credentials exist.",
        )
        _render_filtered_table(_warehouse_layers(), query)

    if _match(query, "dbt models staging marts"):
        section_heading(
            "dbt Model Inventory",
            "dbt owns the inspectable SQL transformation layer. The model names are intentionally "
            "plain because they are part of the operating contract for reviewers and future maintainers.",
        )
        _render_filtered_table(_dbt_model_catalog(), query)

    with st.expander("Modeling standards used by this project", expanded=not query):
        st.markdown(
            """
            **Name by role.** Staging models should describe source normalization. Mart models should
            describe analytical use.

            **Keep transformations inspectable.** SQL models should carry business logic that belongs
            in the warehouse. Python should handle acquisition, file handling, and app-facing glue.

            **Preserve source meaning.** Raw source columns should not be renamed casually. Renaming
            belongs in Silver, where project-owned terminology is introduced deliberately.

            **Protect Gold.** Gold tables are allowed to be boring. Their job is to be stable, readable,
            and dependable for dashboards.
            """
        )


def _render_orchestration(query: str) -> None:
    if _match(query, "airflow orchestration dag run order"):
        section_heading(
            "Airflow Orchestration Design",
            "Airflow is the run-control plane. It should make execution order, retries, and failure "
            "points explicit without hiding the business transformation logic inside operators.",
        )
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "DAG family": "Source ingestion",
                        "Tasks": "FDIC, FRED, QBP, NIC bootstrap runs",
                        "Architecture note": "Source-specific acquisition is isolated from modeling.",
                    },
                    {
                        "DAG family": "Transform and quality",
                        "Tasks": "dbt build, quality checkpoint, mart export",
                        "Architecture note": "Warehouse contracts are built after raw acquisition.",
                    },
                    {
                        "DAG family": "Control-plane sync",
                        "Tasks": "Postgres telemetry and status sync",
                        "Architecture note": "Operational metadata is synchronized separately from business facts.",
                    },
                ]
            ),
            width="stretch",
            hide_index=True,
        )

    with st.expander("Airflow design principles for this repo", expanded=not query):
        st.markdown(
            """
            **DAGs coordinate, they do not model.** A DAG should call ingestion scripts, dbt builds,
            quality checks, and sync jobs. It should not become the place where business metrics are
            defined.

            **Failures must be locatable.** A failed source pull, failed transformation, failed quality
            gate, and failed control-plane sync should appear as separate operational concerns.

            **Local parity matters.** The same scripts Airflow calls should also be runnable locally.
            This keeps debugging practical and avoids creating an orchestrator-only code path.
            """
        )


def _render_warehouse(query: str) -> None:
    if _match(query, "snowflake warehouse database schema"):
        section_heading(
            "Snowflake Warehouse Design",
            "Snowflake is the target analytical warehouse for the resume-grade version. The repo "
            "defines separate raw, staging, intermediate, and marts databases so each layer has a clear role.",
        )
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Database": "FINLENS_RAW",
                        "Purpose": "Landing tables with VARIANT raw payloads and ingest metadata.",
                    },
                    {
                        "Database": "FINLENS_STAGING",
                        "Purpose": "Typed source-normalized structures built from raw payloads.",
                    },
                    {
                        "Database": "FINLENS_INTERMEDIATE",
                        "Purpose": "Reusable transformations that support multiple marts.",
                    },
                    {
                        "Database": "FINLENS_MARTS",
                        "Purpose": "Business-consumption layer for Streamlit and API reads.",
                    },
                ]
            ),
            width="stretch",
            hide_index=True,
        )

    if _match(query, "s3 landing partition"):
        section_heading(
            "S3 Landing Pattern",
            "S3 is the evidence boundary. Files are written by source and ingestion date so a run can "
            "be replayed, audited, or loaded into Snowflake without depending on the app filesystem.",
        )
        st.code(
            "s3://<raw-bucket>/source=<fdic|fred|qbp|nic>/ingestion_date=YYYY-MM-DD/<uuid>.json",
            language="text",
        )

    with st.expander("Warehouse activation boundary", expanded=not query):
        st.markdown(
            """
            The local product currently uses DuckDB to keep the application runnable without paid
            infrastructure. The Snowflake contract is still meaningful: DDL, load scripts, dbt profiles,
            and model names are in place so the warehouse can be activated when credentials are supplied.

            The important architectural constraint is that Streamlit should not care whether the Gold
            output came from DuckDB locally or Snowflake in the deployed stack. The UI contract should
            stay the same.
            """
        )


def _render_quality(query: str) -> None:
    if _match(query, "quality tests reconciliation data quality"):
        section_heading(
            "Data Quality Strategy",
            "Quality checks are split by responsibility. dbt should own structural model tests, while "
            "Great Expectations remains available for richer statistical or checkpoint-oriented checks.",
        )
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Check type": "Source readiness",
                        "Owner": "Connector report",
                        "Example": "FRED is missing API key; QBP URL is not supplied.",
                    },
                    {
                        "Check type": "Structural model checks",
                        "Owner": "dbt",
                        "Example": "Not-null keys, accepted values, relationship integrity.",
                    },
                    {
                        "Check type": "Aggregate reconciliation",
                        "Owner": "Gold / Control Room",
                        "Example": "QBP totals compared against Gold stress-pulse aggregates.",
                    },
                    {
                        "Check type": "Operational run state",
                        "Owner": "Pipeline status model",
                        "Example": "FDIC to Bronze succeeded; QBP to Bronze missing data.",
                    },
                ]
            ),
            width="stretch",
            hide_index=True,
        )

    with st.expander("Why reconciliation matters", expanded=not query):
        st.markdown(
            """
            Reconciliation is stronger than a decorative dashboard metric. It tells a reviewer whether
            the engineered dataset agrees with an external authority. In FinLens, the QBP contract is
            the correct place to validate industry-level totals before the Stress Pulse surface depends
            on them.
            """
        )


def _render_decisions(query: str) -> None:
    section_heading(
        "Data Architecture Decision Register",
        "These are the operating decisions that determine how the platform stays maintainable.",
    )
    _render_filtered_table(_decision_register(), query)

    if _match(query, "security secrets privacy"):
        with st.expander("Security and privacy operating rules", expanded=not query):
            st.markdown(
                """
                Secrets stay in `.env`, deployment secrets, or the target cloud secret store. They do
                not belong in source code, markdown, SQL, notebooks, screenshots, or logs.

                The current code works inside the FinLens project tree. It does not require access to
                personal folders, system files, or unrelated databases. Runtime sync is limited to the
                explicit Postgres DSN supplied by the operator.
                """
            )

    if _match(query, "deferred removed sec fr y-9c sloos ubpr"):
        with st.expander("Removed scope", expanded=not query):
            st.markdown(
                """
                SEC filings, FR Y-9C, SLOOS, UBPR, active Stress Lab modeling, and filing surveillance
                are not part of the active build. They were removed because they add schema ambiguity,
                access friction, or maintenance cost before they add enough value to the core portfolio
                demonstration.
                """
            )


def _render_theory(query: str) -> None:
    section_heading(
        "Data Architecture Theory",
        "This section explains the platform tools in the context of this project. It is not vendor "
        "marketing copy; it is the engineering rationale for why each tool exists in the stack.",
    )

    topics = [
        (
            "AWS S3",
            "In a data platform, object storage is usually the first durable control point. FinLens "
            "uses S3 as the intended Bronze zone so source pulls can be retained independently from "
            "the warehouse, replayed during debugging, and inspected when downstream numbers look wrong. "
            "That design matters because a dashboard without raw retention has no credible audit path.",
        ),
        (
            "Airflow",
            "Airflow is the orchestration plane, not the transformation engine. Its value is dependency "
            "management: FDIC and FRED acquisition must complete before modeling; dbt must complete "
            "before serving checks; control-plane sync should run after status is known. Keeping these "
            "steps explicit makes failures diagnosable instead of hiding them inside one large script.",
        ),
        (
            "dbt",
            "dbt is the warehouse modeling layer. It is where source-shaped data becomes analytical "
            "data. In FinLens, staging models normalize source payloads, intermediate models carry "
            "shared shaping, and mart models become Gold contracts for Streamlit. That split is important "
            "because it gives reviewers a clear path from raw source to business metric.",
        ),
        (
            "Snowflake",
            "Snowflake is the target enterprise warehouse. The project separates raw, staging, "
            "intermediate, and marts databases to make ownership clear. Raw tables preserve payloads, "
            "staging tables type and normalize them, intermediate tables support reusable logic, and "
            "marts are the consumption boundary. That is the architecture story hiring managers expect "
            "from a data engineering portfolio.",
        ),
        (
            "Terraform",
            "Terraform gives the infrastructure layer the same review discipline as application code. "
            "Buckets, IAM boundaries, and warehouse-adjacent resources should be declared rather than "
            "remembered. For FinLens, Terraform is less about complexity and more about showing that "
            "cloud resources are reproducible.",
        ),
        (
            "Great Expectations",
            "Great Expectations is reserved for quality checks that are awkward to express as simple SQL "
            "tests. dbt is still the primary model-test layer. GE becomes useful for checkpoint-style "
            "validation, row-count ranges, distribution checks, and source-to-serving quality reports.",
        ),
        (
            "DuckDB",
            "DuckDB is the local analytical runtime. It keeps the project useful before Snowflake is "
            "activated and allows tests to run without cloud cost. It is not a replacement for the "
            "resume-grade warehouse story; it is the development and fallback engine.",
        ),
    ]

    for title, body in topics:
        if not _match(query, title, body):
            continue
        with st.expander(title, expanded=bool(query)):
            st.markdown(body)
            if title in REFERENCE_LINKS:
                st.markdown(f"Official reference: [{title}]({REFERENCE_LINKS[title]})")

    section_heading("Glossary", "Core data-architecture terms used by FinLens.")
    _render_filtered_table(_glossary(), query)

    section_heading("Official References", "Primary vendor documentation for deeper study.")
    _render_filtered_table(_external_references(), query)


def render_architecture_decisions() -> None:
    section_heading(
        "Architecture Decisions",
        "Internal data architecture handbook for FinLens. This section documents the stack, data "
        "contracts, modeling standards, orchestration design, warehouse boundary, and activation path.",
    )
    query = st.text_input(
        "Search architecture knowledge base",
        placeholder="Search S3, Airflow, dbt, Snowflake, contracts, lineage, quality...",
        key="architecture_decision_search",
    ).strip()

    tabs = st.tabs(
        [
            "Platform",
            "Data Modeling",
            "Orchestration",
            "Warehouse",
            "Quality",
            "Decisions",
            "Theory",
        ]
    )
    with tabs[0]:
        _render_platform(query)
    with tabs[1]:
        _render_data_modeling(query)
    with tabs[2]:
        _render_orchestration(query)
    with tabs[3]:
        _render_warehouse(query)
    with tabs[4]:
        _render_quality(query)
    with tabs[5]:
        _render_decisions(query)
    with tabs[6]:
        _render_theory(query)
