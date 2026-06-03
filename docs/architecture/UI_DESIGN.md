# FinLens — UI Design (UI Gate, pre-implementation)

Status: DRAFT — pending 30-yr UI-architect design sign-off at 100% before any build.
Supersedes the rejected marketing-landing design. Aesthetic: serious engineering console
(Datadog / Linear / Grafana-grade), dark, dense, filterable — NOT an AI-startup landing page.
Every existing visualization and all content across all three verticals is preserved.

## 1. Global shell (persistent on every screen)
Top bar: brand (left) · **surface switcher** (center): `Business · Data Engineering · Machine
Learning  |  Wiki · Architecture` — the three verticals grouped, Wiki and Architecture as
separate top-level switches · right: live **Model API** status badge (online/version/latency)
+ a Home link. The switcher is persistent everywhere so you can jump surfaces from anywhere.

Layout within a surface = **left rail (section tabs) + main panel area**. The left rail lists
that surface's sections; the main area renders the selected section as dense panels. Section
switching is in-page (no reload), URL hash-synced (deep-linkable, back-button works).

## 2. Home
- The use-notice disclaimer (personal project, public data, not advice).
- A brief, concrete project intro (what it is, the data, one honest headline metric).
- Three large link cards → Business / Data Engineering / Machine Learning, each with a
  one-line description + a tiny live stat. Secondary links: Wiki, Architect's Desk.

## 3. Verticals (left-rail tabbed; all content preserved)
**Business** — sections: Stress Pulse · Failure Forensics · Macro Transmission. Each renders the
existing analyses as charts (ECharts): industry stress over time, failures by year/geography/
acquirer, macro series + transmission. Filters: year range, state, metric.

**Data Engineering** — sections: Live Pipeline (DAG run status, freshness, flow health) ·
Source Contracts (per-source schema/SLA/cadence) · Medallion Layers (bronze/silver/gold with
row counts) · Data Quality (Great Expectations checkpoints, pass/fail) · Lineage (source→mart
graph) · Stack · Architecture Decisions (ADRs). Top-right button: **"Open DE Architecture →"**
(deep-link to Architect's Desk → DE tab). Filters: layer, source, status.

**Machine Learning** — sections: Model Overview (headline metrics, champion version) ·
Performance (PR curve, ROC-by-year, recall@k) · Calibration (reliability, ECE, top-decile) ·
Explainability (global SHAP) · Drift (Evidently data + prediction drift) · Governance (SR 26-2,
fairness scoping, limits) · **Live Stress Lab** (the existing real-bank fact-check + hypothetical
sliders with live /predict). Top-right: **"Open ML Architecture →"**. Filters: horizon, cohort,
segment.

## 4. Wiki (separate top-level)
Left rail = article tree (clusters → branches → articles), search box, in-page switching (no
reload — st-style buttons replaced by hash nav). Main = the article (theory): hazard models,
calibration, PR-AUC, SHAP, drift, medallion, dbt, Airflow, banking concepts. Enriched content.

## 5. Architect's Desk (separate top-level) — the centerpiece map
- **Home (Flow Map)**: a single interactive end-to-end diagram (DAG) of the whole system:
  Sources (FDIC/FRED) → Ingestion → Bronze → Silver → Intermediate → Gold marts → ┬→ Business
  surfaces; └→ ML feature panel → Training (LightGBM+calibration) → Registry (champion) →
  Serving (FastAPI + audit log) → Monitoring (Evidently) → ML surfaces. Every node is a
  **clickable button** → opens that component's detail page (what it is, tech, $0 mapping,
  inputs/outputs, the real artifact/code path). Rendered with a graph lib (ECharts graph/
  Mermaid-style) — pan/zoom, hover highlights the data path, click navigates.
- **Tabs**: **Data Engineering Architecture** (ingestion→medallion→quality→serving, component
  cards + the DE slice of the DAG) and **Machine Learning Architecture** (panel→features→
  splits→model→calibration→registry→serving→audit→monitoring→retrain DAG, component cards +
  the ML slice). These are the deep-link targets from the DE / ML verticals.
- Each component detail = real: name, production-reference tool, $0 counterpart, label
  (LIVE/LOCAL/REFERENCE), the file/artifact it maps to. Sourced from PRODUCTION_ARCHITECTURE.md.

## 6. Visual system (dopamine, done seriously)
Dark console palette (near-black canvas, elevated panels, one accent + status colors). Strong
type hierarchy, tabular figures, 8-pt grid. Dense but breathable. Micro-interactions: hover
states, smooth section transitions, number count-ups, chart entrance animation, the DAG
path-highlight on hover. Researched dopamine drivers applied tastefully: immediate feedback,
progressive reveal, a single satisfying "hero" data moment per surface (e.g., the failures
timeline, the PR curve, the live gauge), consistent rhythm, zero layout jank. Fully responsive;
WCAG-AA contrast; decisions shown as text+color (not color alone); prefers-reduced-motion honored.

## 7. Tech (same $0 stack)
Bespoke HTML/CSS/JS served by FastAPI StaticFiles; ECharts (vendored). Data from baked JSON
(`export_web_data.py`, extended for the DE/architecture/wiki/business panels) + live `/predict`
+ `/ready`. SPA-style hash router for surfaces/sections (no framework, no build step, no cost).

## 7a. Resolved design-gate blockers (the hard, fabrication-prone 20%)

**(B1+B6) The DAG + component pages are driven by ONE source of truth.** A committed
`web/data/architecture_graph.json` is the single source for the flow map, the DE/ML slices,
and every component detail page. One object per node:
`{id, label, layer: de|ml|shared, status: LIVE|LOCAL|REFERENCE, route: "#/desk/c/<id>",
prod_ref, zero_dollar, artifact_path}`. Generated by `export_web_data.py` from
PRODUCTION_ARCHITECTURE.md B.2/B.3; a CI check asserts every `artifact_path` exists in the repo
(un-fabricable). Nodes (LR-layered):
`fdic_src, fred_src → ingest → bronze → silver → intermediate → gold → {business_surfaces ;
feature_panel → train → calibrate → registry → serving(+audit) → monitoring → ml_surfaces}`.
Edges = that chain (explicit list in the JSON). Layout: fixed left→right layered DAG (dagre/
hand-positioned coords, NOT force-directed). Slice = filter nodes by `layer in {de|shared}` or
`{ml|shared}`. Click a node → `#/desk/c/<id>` detail page rendered from that one object. The
DAG has a screen-reader table fallback and keyboard-activatable nodes.

**(B2) Charts are RE-AUTHORED in ECharts to the same data contract — "preserved" = semantic/
visual parity, not literal reuse.** Existing visuals are Plotly in Streamlit; they are re-built
in ECharts from baked JSON. Inventory ported (parity required): failures timeline, earnings,
funding cost, NIM, asset-quality, unrealized-losses (Business); pipeline DAG (DE); PR curve,
ROC-by-year, calibration, SHAP, drift (ML). Each must match its Streamlit source in data + intent.

**(B3) Quality & lineage are backed by REAL artifacts, labelled honestly.** "Data Quality" panel
renders **dbt test results** (`dbt_quality_summary`/`dbt_results`) — the artifact that exists —
not a fictional GX-checkpoint viewer (GX dir exists but is not the surfaced source; said plainly).
"Lineage" is rendered from the **dbt manifest graph** (a real artifact), not hand-drawn.

**(B5) The Model-API badge cannot lie, because the SITE IS SERVED BY `finlens_ml.serve`** (which
both mounts the static `web/` and exposes `/predict` + `/ready`). So whenever the site is up, the
API is the same process → the badge reflects a real `/ready` call. Honest states: `online vN ·
Nms` (ready 200) / `offline` (ready 503 / model artifact missing). Never a hardcoded "online."
The deployed `api/` container (DE marts) is separate and unchanged; the portfolio site runs on
`finlens_ml.serve`. The Lab `st.stop()`-equivalent: if `/ready` is 503, the Lab shows an honest
"model not loaded" state, no fake numbers.

## 7b. Content-parity map (proves ZERO loss — every existing section gets a home)
| Existing (Streamlit) section/widget | New home |
|---|---|
| Stress Pulse, Failure Forensics, Macro Transmission + charts | Business ▸ same-named tabs |
| Business Knowledge: Business Map, Sources, Metric Dictionary, Transformation Logic, Current Readouts | Business ▸ Knowledge (sub-tabs) |
| Under-the-Hood: Live Pipeline, freshness, Airflow Run Results | Data Engineering ▸ Live Pipeline |
| Source Contracts | DE ▸ Source Contracts |
| Engineering Stack | DE ▸ Stack |
| Data Quality, dbt node results, Reconciliation Controls | DE ▸ Data Quality |
| Data Browser (paginated warehouse tables) | DE ▸ Data Browser |
| Transformation Rule Catalog, Transform Preview (before/after) | DE ▸ Transforms |
| Code Excerpts (ingestion / Airflow / dbt / serving tabs) | DE ▸ Code (or Architect's Desk component pages) |
| Architecture Decisions (ADRs) | DE ▸ ADRs (+ linked from Architect's Desk) |
| Administration | DE ▸ Administration |
| lineage (prose) | DE ▸ Lineage (dbt-manifest graph) |
| AI: Model Pulse/Overview, Feature Contracts (monotone), Stack | ML ▸ Overview / Feature Contracts |
| AI: Model Quality, Performance, Calibration | ML ▸ Performance / Calibration |
| AI: Explainability (SHAP), Drift | ML ▸ Explainability / Drift |
| AI: Model Decisions, Model Card, Governance, Administration | ML ▸ Governance |
| Predictive Analytics Live Lab (real bank + hypothetical) | ML ▸ Live Stress Lab |
| Wiki articles | Wiki (separate surface) |
A build-time check lists any existing section not present in this map → fails the parity gate.

## 7c. Adopted improvements
- Filters are **hash-encoded** (shareable), persisted within a surface, reset on surface switch.
- Deep links: DE ▸ "Open DE Architecture" → `#/desk/de`; ML → `#/desk/ml`; back-link returns to
  the originating vertical. Component pages: `#/desk/c/<id>`.
- **Hero data moment per surface** (entrance animation + count-up): Business = failures timeline;
  DE = live pipeline DAG; ML = PR curve + live gauge; Desk = the flow map.
- Degraded states defined: model offline, missing drift report, empty cohort → honest empty UI.
- DAG: `prefers-reduced-motion` honored, keyboard-navigable nodes, table fallback.

## 8. Acceptance (UI gate enforces)
One cohesive serious console (not a pitch); all 3 verticals + Wiki + Architect's Desk present
with full content + visualizations; persistent surface switch; in-page tabbed sections (no
reload); the interactive clickable DAG works and routes to component pages; DE/ML verticals
deep-link to their architecture tabs; filters work; genuine visual polish/"dopamine"; 2026
banking-production standard; nothing fabricated; $0; fast; responsive; accessible.
