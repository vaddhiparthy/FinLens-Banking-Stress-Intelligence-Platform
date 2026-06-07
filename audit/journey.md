# Ceiling A: user journey (desktop, 1440x900)

A walkthrough of every surface a visitor can reach, what it shows, and the evidence that it
renders live. Screenshots are in audit/screenshots/ (e2e_*.png are the automated 1440x900
captures; the numbered set is the prior per-section sweep). Automated assertions: audit/playwright/results.xml (8/8 pass).

## Entry — Home (`/`)
The persistent chrome loads: surface dropdown (left), FinLens wordmark (center), author credit
(right), and a section tab row. The home hero introduces the product and routes to the three
surfaces. Evidence: e2e_home.png; test "home surface renders the brand and entry".

## Business surface
- **Stress Pulse** (`/Stress_Pulse`): macro/banking stress snapshot.
- **Failure Forensics** (`/Failure_Forensics`): historical bank-failure exploration.
- **Macro Transmission** (`/Macro_Transmission`): FRED macro-to-banking linkage.
- **Early Warning** (`/Early_Warning`): the live model surfaced for a business reader — score a
  bank, see the holdout evidence and a what-if. Evidence: e2e_early_warning.png.
- **Analyst Assistant** (`/Analyst_Assistant`): a cited RAG chatbot. A cached demonstration
  answer renders instantly (retrieval + citations are real); an "Ask live" box runs the local
  model (~30s). The "How this works" expander now reads its eval metrics from
  rag/eval_report.json. Evidence: e2e_assistant.png; test asserts the cached answer and the
  "Ask live" affordance.

## Data Engineering surface (`/Data_Engineering`)
Six sections via the tab row, each its own real artifact:
- **Live Pipeline**: source→bronze→silver→gold Sankey + per-flow runtime status table + an
  interactive warehouse data browser. Evidence: e2e_de_pipeline.png.
- **Data Quality**: reconciliation controls, dbt build summary (11 models / 7 tests / 0 fail),
  dbt node results, and the **Great Expectations suite result (20/20)** with a per-expectation
  pass/fail table (newly surfaced, A-003). Evidence: e2e_de_quality_gx.png; test asserts the GX
  block renders.
- **Source Contracts**: source activation, warehouse inventory, transform preview + rule catalog.
- **Engineering Stack**: tool-evidence, platform-stack readiness, Airflow runs, latest pipeline
  run, warehouse activation checklist, and code excerpts.
- **Administration**: service endpoints (now including the **ML serving routes**
  /predict-failure-risk, /predict, /predict/batch, /ready on :8077), control-sync, freshness,
  landing artifacts, and a **Containerization & Kubernetes deploy block** (Dockerfiles, compose,
  kind config + ml-serve manifest with the deploy recipe) — newly surfaced (A-003).
- **Architecture Decisions**: the architecture handbook.

## AI Engineering surface (`/AI_Engineering`)
Eight sections:
- **Pipeline**: now opens with a **6-stage flow diagram** (Ingest→Features→Label→Split→
  Train+calibrate→Serve+monitor) carrying live metrics, then the bulleted pipeline and the real
  source code (labels/splits/train) pulled via inspect.getsource. Evidence: e2e_ai_pipeline.png.
- **Notebook**: the executed analysis notebook embedded.
- **Feature Contracts**: SHAP importance + correlation + the monotone contract table.
- **ML Stack**: the open-source $0 stack table.
- **Model Quality**: leads with a 4-metric hero (PR-AUC 0.301, ROC 0.855, recall@200 54.5%, ECE
  1.2e-4), then PR/ROC/calibration/score/threshold/capacity charts, the failure-type
  decomposition, pooled-vs-addressable across 5 families, the GRU challenger, and drift. The deep
  validator content (tuning search, interval coverage, and the **robustness cross-checks** —
  calibration bake-off, CBLR break, competing-risks/Fine-Gray, point-in-time vs restated) is now
  collapsed into expanders (A-002, A-006). Evidence: e2e_ai_quality.png; test asserts the hero
  metric and the cross-checks heading render.
- **Model Decisions**: the key choices, the full model card, and the six **methodology
  write-ups** as expanders (A-004). Evidence: e2e_ai_decisions.png.
- **Administration**: registry, promotion, retrain, rollback, $0 guard, with live registry code.
- **Wiki**: concept reference.

## Wiki surface (`/Wiki`)
The encyclopedia: one article per page with a section tree and deep content.

## Cross-cutting
- The active section tab now renders as an accent-tinted pill with a 3px underline (A-008),
  visible in every e2e screenshot.
- Accessibility: 0 axe violations on all 5 audited pages (audit/axe/*.json).
