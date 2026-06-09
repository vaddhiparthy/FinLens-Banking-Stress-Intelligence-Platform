# ruff: noqa: E501
"""Dedicated whole-system architecture diagram for the FinLens Wiki.

The diagram is real Graphviz DOT rendered client-side by ``st.graphviz_chart`` (no binary, no
network), so it stays accurate and portable. The companion article walks every layer in depth.
Edit the DOT here and the wiki page picks it up via the article's ``diagram`` marker.
"""

from __future__ import annotations

# Palette mirrors the light theme so the diagram reads as part of the product, not a bolt-on.
ARCHITECTURE_DOT = """
digraph FinLens {
  rankdir=LR;
  bgcolor="transparent";
  compound=true;
  splines=spline;
  nodesep=0.34;
  ranksep=0.85;
  fontname="Helvetica";
  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11,
        color="#e4d7c6", fillcolor="#fffaf3", penwidth=1.4, margin="0.20,0.11"];
  edge [color="#7f6b58", penwidth=1.1, arrowsize=0.75,
        fontname="Helvetica", fontsize=9, fontcolor="#6a6b74"];

  subgraph cluster_src {
    label="Public data sources"; labeljust="c"; fontsize=12; fontname="Helvetica-Bold";
    style="rounded,filled"; fillcolor="#f5efe6"; color="#e4d7c6";
    fdic [label="FDIC BankFind\\n+ Failed Bank List", tooltip="FDIC BankFind API + the public Failed Bank List: institutions and every U.S. bank failure since 2000."];
    qbp  [label="FDIC Quarterly\\nBanking Profile", tooltip="FDIC Quarterly Banking Profile: industry-aggregate earnings, asset quality, and capital by quarter."];
    fred [label="FRED / ALFRED\\nmacro series", tooltip="Federal Reserve Economic Data (St. Louis Fed), point-in-time aware via ALFRED: unemployment, Treasury yields, credit spreads, CPI, housing."];
    nic  [label="FFIEC National\\nInformation Center", tooltip="FFIEC National Information Center: institution identity and parent-company relationships."];
  }

  subgraph cluster_bronze {
    label="Ingestion · Bronze  (VPS local filesystem)"; labeljust="c"; fontsize=12; fontname="Helvetica-Bold";
    style="rounded,filled"; fillcolor="#f3dfcf"; color="#e4d7c6";
    ingest [label="Python ingestion clients\\nretry · watermarks · DLQ", tooltip="Per-source Python clients with retry/backoff and watermarks; bad payloads go to a dead-letter queue."];
    raw    [label="data/raw/source=*/\\ningestion_date=*  (Hive)", fillcolor="#ffffff", tooltip="Immutable raw snapshots on the VPS local filesystem, Hive-partitioned by source and ingestion date. No cloud object store."];
    rotate [label="Rotation policy\\n1 version / source", fillcolor="#ffffff", tooltip="Retention: keeps exactly one version per source and purges older ingestion_date partitions to keep the VPS small."];
  }

  subgraph cluster_xform {
    label="Transform · dbt"; labeljust="c"; fontsize=12; fontname="Helvetica-Bold";
    style="rounded,filled"; fillcolor="#dbeceb"; color="#cfe0df";
    silver [label="Silver\\nstaging models", tooltip="dbt staging models normalise raw payloads into canonical, typed tables with stable column names."];
    inter  [label="Intermediate\\nreusable joins", tooltip="dbt intermediate models hold reusable joins/enrichments shared by multiple marts."];
    gold   [label="Gold marts\\nfacts + dimensions", tooltip="The consumption contract: fact and dimension tables the dashboards and API read. Nothing reads below Gold."];
    duck   [label="DuckDB\\nwarehouse of record", fillcolor="#ffffff", tooltip="In-process columnar warehouse that runs the live deployment at $0; MotherDuck is the cloud-scale DuckDB path."];
    snow   [label="Snowflake\\noptional · credential-gated", style="rounded,filled,dashed", fillcolor="#ffffff", tooltip="Optional warehouse-grade target via a credential-gated dbt output; not the live path (trial expired)."];
  }

  subgraph cluster_ml {
    label="AI Engineering · ML"; labeljust="c"; fontsize=12; fontname="Helvetica-Bold";
    style="rounded,filled"; fillcolor="#efe3f3"; color="#e3d3eb";
    panel [label="bank_quarterly_risk_facts\\n448,661 rows · 34 features", tooltip="The modelling panel: 448,661 bank-quarters across ~8,800 banks, 2008Q1–2026Q1, 34 CAMELS-aligned features."];
    model [label="Discrete-time hazard\\nLightGBM · monotone\\ncalibrated · 12-seed bag", tooltip="Calibrated, monotone-constrained, 12-seed bagged LightGBM hazard model scoring 4-quarter distress probability."];
    art   [label="Artifacts\\nmetrics · SHAP · viz", fillcolor="#ffffff", tooltip="Training outputs: OOT metrics, calibration, SHAP attributions, and chart data consumed by the surfaces."];
  }

  subgraph cluster_serve {
    label="Serving"; labeljust="c"; fontsize=12; fontname="Helvetica-Bold";
    style="rounded,filled"; fillcolor="#f5efe6"; color="#e4d7c6";
    streamlit [label="Streamlit surfaces\\nBusiness · Data Eng · AI · Wiki", tooltip="The four UI surfaces; they read only Gold marts and model artifacts, never source-shaped data."];
    api       [label="FastAPI\\nhealth · telemetry · scores", tooltip="Machine-facing endpoints: health, telemetry, and model scoring for monitoring and integrations."];
    chat      [label="Assistant (RAG)\\nretrieval + cited answers\\nLLM synthesis + extractive fallback", tooltip="Retrieval-augmented assistant: retrieves cited regulator filings + live model score, synthesises via OpenRouter, falls back to a cited extractive answer."];
  }

  subgraph cluster_ops {
    label="Orchestration · Quality"; labeljust="c"; fontsize=12; fontname="Helvetica-Bold";
    style="rounded,filled"; fillcolor="#f4efe6"; color="#e4d7c6";
    airflow [label="Airflow\\nthin DAGs", tooltip="Schedules ingestion and transforms via thin DAGs that call the same Python entry points used locally."];
    quality [label="Great Expectations\\ndbt tests · reconciliation", tooltip="Layered quality: Great Expectations suites, dbt structural tests, and runtime reconciliation against external authority."];
  }

  fdic -> ingest; qbp -> ingest; fred -> ingest; nic -> ingest;
  ingest -> raw;
  raw -> rotate [style=dashed, label="retain 1"];
  raw -> silver [label="build"];
  silver -> inter -> gold;
  silver -> duck [style=dotted, dir=none];
  gold -> duck [dir=both];
  duck -> snow [style=dashed, label="optional"];
  gold -> streamlit [label="reads Gold"];
  gold -> api;
  gold -> panel;
  panel -> model -> art;
  art -> api;
  art -> streamlit;
  duck -> chat [style=dotted, dir=none];
  art -> chat [style=dotted, dir=none];
  chat -> streamlit;
  // Control-flow, NOT data-flow: Airflow's thin DAGs schedule the Python ingestion and the dbt
  // build (they call the same entry points; data does not pass through Airflow). Distinct colour +
  // open arrowhead + "schedules" label so these never read as a data source feeding Python.
  airflow -> ingest [style=dashed, color="#9a86b8", fontcolor="#9a86b8", fontsize=8.5, label="schedules", arrowhead=vee, constraint=false];
  airflow -> silver [style=dashed, color="#9a86b8", fontcolor="#9a86b8", fontsize=8.5, label="schedules", arrowhead=vee, constraint=false];
  // Association, not flow: Great Expectations validates these layers (no data moves along the edge).
  quality -> raw [style=dotted, dir=none, color="#5f9e87", fontcolor="#5f9e87", fontsize=8.5, label="validates", constraint=false];
  quality -> gold [style=dotted, dir=none, color="#5f9e87", fontcolor="#5f9e87", fontsize=8.5, label="validates", constraint=false];
}
"""

_BODY = """\
The diagram above is the whole platform on one page. It is real Graphviz, not a screenshot, so it
cannot drift from the description below. Read it left to right: public data enters on the left,
becomes governed Gold in the middle, and is served to people and machines on the right, with
orchestration, quality, and deployment wrapping the whole thing.

### 1. Public data sources
Four free, official feeds: **FDIC BankFind** and the Failed Bank List (institutions and failure
events), the **FDIC Quarterly Banking Profile** (industry aggregates), **FRED/ALFRED** (macro
series, point-in-time aware), and the **FFIEC National Information Center** (institution and parent
metadata). Nothing here is paid or scraped; every source has a documented contract.

### 2. Ingestion · Bronze (on the VPS local filesystem)
Python ingestion clients pull each source with retry and watermarks, and route bad payloads to a
dead-letter queue. Raw artefacts land verbatim on the **VPS local filesystem**, Hive-partitioned as
`data/raw/source=<src>/ingestion_date=<date>/<uuid>.json` — there is no cloud object store. A
**rotation policy** keeps exactly one version per source and purges older partitions, so the landing
zone stays small on a minimal VPS. Bronze is immutable and replayable: a reviewer can list it and
see exactly what each source returned.

### 3. Transform · dbt
dbt builds the medallion layers on top of **DuckDB**, the warehouse of record: **Silver** staging
models normalise raw payloads into canonical typed tables, **Intermediate** holds reusable joins,
and **Gold** marts are the stable consumption contract (facts and dimensions). **Snowflake** is
wired as an optional, credential-gated output for a warehouse-grade target, but DuckDB runs the live
deployment at $0.

### 4. AI Engineering · ML
The `bank_quarterly_risk_facts` panel (448,661 bank-quarters, 34 CAMELS-aligned features) feeds a
**discrete-time hazard model**: a calibrated, monotone, 12-seed bagged LightGBM that scores each
bank's probability of failing within four quarters. Training emits artefacts (metrics, SHAP
attributions, chart data) consumed by the serving layer.

### 5. Serving
**Streamlit** renders the four surfaces (Business, Data Engineering, AI Engineering, and this Wiki)
and reads only Gold and the model artefacts. **FastAPI** publishes health, telemetry, and scoring
endpoints for machines and monitoring. The **assistant** is a retrieval-augmented chat: it retrieves
cited regulator filings and live model scores, synthesises an answer with an LLM, and falls back to a
fully-cited extractive answer if the model is unavailable.

### 6. Orchestration · Quality
**Airflow** schedules ingestion and transforms through deliberately thin DAGs that call the same
Python entry points used locally, so there is no orchestrator-only code path. Quality is layered:
**Great Expectations** suites, **dbt tests**, and **runtime reconciliation** against external
authority each guard a different boundary.

For the reasoning behind each tool choice, see [[Tooling Choices and Their Rationale]]; for the
layer model in detail, see [[Bronze, Silver, Intermediate, Gold]] and [[Why Dashboards Read Gold Only]].
"""

_PANZOOM_JS = """
<script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"></script>
<script>
(function () {
  var doc;
  try { doc = window.parent.document; } catch (e) { return; }  // degrade: diagram still renders
  var tries = 0;
  function init() {
    tries += 1;
    var svg = doc.querySelector('[data-testid="stGraphVizChart"] svg, .stGraphVizChart svg');
    if (!svg) { if (tries < 80) setTimeout(init, 150); return; }
    if (svg.getAttribute('data-panzoom') === '1') return;
    if (typeof window.svgPanZoom === 'undefined') { if (tries < 80) setTimeout(init, 150); return; }
    svg.setAttribute('width', '100%');
    svg.setAttribute('height', '100%');
    svg.setAttribute('data-panzoom', '1');
    try {
      window.svgPanZoom(svg, {
        zoomEnabled: true, controlIconsEnabled: true, fit: true, center: true,
        minZoom: 0.3, maxZoom: 12, zoomScaleSensitivity: 0.4, dblClickZoomEnabled: true
      });
    } catch (e) { /* leave the static diagram in place */ }
  }
  init();
})();
</script>
"""


def render_architecture() -> None:
    """Render the architecture diagram with scroll-zoom, drag-to-pan, and on-diagram controls.

    The DOT is rendered by Streamlit's client-side Graphviz (robust, no network needed to draw it).
    A small ``svg-pan-zoom`` layer is attached on top; if its CDN is unavailable the diagram still
    renders, just without the pan/zoom controls (graceful degradation).
    """
    import streamlit as st
    from streamlit.components.v1 import html as _html

    st.markdown(
        """
        <style>
        [data-testid="stGraphVizChart"], .stGraphVizChart {
            height: 560px; border: 1px solid #e4d7c6; border-radius: 14px;
            background: #fffaf3; overflow: hidden;
            box-shadow: 0 8px 24px rgba(15, 23, 42, .05);
        }
        [data-testid="stGraphVizChart"] > svg, .stGraphVizChart > svg {
            width: 100% !important; height: 100% !important;
        }
        .svg-pan-zoom-control-background { fill: #fffaf3; opacity: .85; }
        .svg-pan-zoom-control-element { fill: #bf6d47; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.graphviz_chart(ARCHITECTURE_DOT, use_container_width=True)
    st.caption("Scroll to zoom · drag to pan · use the on-diagram controls to zoom in/out and reset.")
    _html(_PANZOOM_JS, height=0)


ARCHITECTURE_ARTICLES = {
    "System Architecture": {
        "cluster": "Architecture",
        "branch": "Architect Desk",
        "diagram": "system_architecture",
        "summary": "The entire FinLens platform on one page: sources, ingestion and Bronze on the "
                   "VPS, dbt Silver/Intermediate/Gold on DuckDB, the ML hazard model, the serving "
                   "surfaces and assistant, orchestration and quality, and the VPS deployment edge.",
        "body": _BODY,
    },
}
