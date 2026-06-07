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
    label="Public data sources"; labeljust="l"; fontsize=12; fontname="Helvetica-Bold";
    style="rounded,filled"; fillcolor="#f5efe6"; color="#e4d7c6";
    fdic [label="FDIC BankFind\\n+ Failed Bank List"];
    qbp  [label="FDIC Quarterly\\nBanking Profile"];
    fred [label="FRED / ALFRED\\nmacro series"];
    nic  [label="FFIEC National\\nInformation Center"];
  }

  subgraph cluster_bronze {
    label="Ingestion · Bronze  (VPS local filesystem)"; labeljust="l"; fontsize=12; fontname="Helvetica-Bold";
    style="rounded,filled"; fillcolor="#f3dfcf"; color="#e4d7c6";
    ingest [label="Python ingestion clients\\nretry · watermarks · DLQ"];
    raw    [label="data/raw/source=*/\\ningestion_date=*  (Hive)", fillcolor="#ffffff"];
    rotate [label="Rotation policy\\n1 version / source", fillcolor="#ffffff"];
  }

  subgraph cluster_xform {
    label="Transform · dbt"; labeljust="l"; fontsize=12; fontname="Helvetica-Bold";
    style="rounded,filled"; fillcolor="#dbeceb"; color="#cfe0df";
    silver [label="Silver\\nstaging models"];
    inter  [label="Intermediate\\nreusable joins"];
    gold   [label="Gold marts\\nfacts + dimensions"];
    duck   [label="DuckDB\\nwarehouse of record", fillcolor="#ffffff"];
    snow   [label="Snowflake\\noptional · credential-gated", style="rounded,filled,dashed", fillcolor="#ffffff"];
  }

  subgraph cluster_ml {
    label="AI Engineering · ML"; labeljust="l"; fontsize=12; fontname="Helvetica-Bold";
    style="rounded,filled"; fillcolor="#efe3f3"; color="#e3d3eb";
    panel [label="bank_quarterly_risk_facts\\n448,661 rows · 34 features"];
    model [label="Discrete-time hazard\\nLightGBM · monotone\\ncalibrated · 12-seed bag"];
    art   [label="Artifacts\\nmetrics · SHAP · viz", fillcolor="#ffffff"];
  }

  subgraph cluster_serve {
    label="Serving"; labeljust="l"; fontsize=12; fontname="Helvetica-Bold";
    style="rounded,filled"; fillcolor="#f5efe6"; color="#e4d7c6";
    streamlit [label="Streamlit surfaces\\nBusiness · Data Eng · AI · Wiki"];
    api       [label="FastAPI\\nhealth · telemetry · scores"];
    chat      [label="Assistant (RAG)\\nretrieval + cited answers\\nLLM synthesis + extractive fallback"];
  }

  subgraph cluster_ops {
    label="Orchestration · Quality"; labeljust="l"; fontsize=12; fontname="Helvetica-Bold";
    style="rounded,filled"; fillcolor="#f4efe6"; color="#e4d7c6";
    airflow [label="Airflow\\nthin DAGs"];
    quality [label="Great Expectations\\ndbt tests · reconciliation"];
  }

  subgraph cluster_deploy {
    label="Edge · Deployment  (single VPS)"; labeljust="l"; fontsize=12; fontname="Helvetica-Bold";
    style="rounded,filled"; fillcolor="#eef1f4"; color="#dde3ea";
    cf      [label="Cloudflare\\nDNS · TLS · Turnstile"];
    caddy   [label="Caddy\\nreverse proxy / ingress"];
    compose [label="Docker Compose\\nStreamlit · FastAPI · Postgres · Uptime Kuma"];
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
  airflow -> ingest [style=dashed];
  airflow -> silver [style=dashed];
  quality -> raw [style=dotted, dir=none];
  quality -> gold [style=dotted, dir=none];
  cf -> caddy -> compose;
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

### 7. Edge · Deployment (single VPS)
**Cloudflare** provides DNS, TLS, and the Turnstile challenge at the edge. **Caddy** is the public
ingress on the VPS, reverse-proxying to a small set of **Docker Compose** containers (Streamlit,
FastAPI, Postgres for control-plane state, Uptime Kuma for monitoring). The deployment is
reproducible from the compose file; there is no infrastructure-as-code because there are no cloud
resources to provision.

For the reasoning behind each tool choice, see [[Tooling Choices and Their Rationale]]; for the
layer model in detail, see [[Bronze, Silver, Intermediate, Gold]] and [[Why Dashboards Read Gold Only]].
"""

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
