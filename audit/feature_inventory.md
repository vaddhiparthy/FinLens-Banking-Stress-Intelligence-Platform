# FinLens Feature Inventory ("show off everything that was built")

Audit of every implemented, presentable feature/capability/metric/artifact in the repo, with
its surfacing status in the Streamlit web UI. Generated from a full crawl of `streamlit_app/`,
`ml/`, `rag/`, `api/`, `dbt/`, `great_expectations/`, `airflow/`, `deploy/`, and `docs/`.

Legend for "Surfaced in UI?":
- A concrete page + section means it is reachable and visible in the running Streamlit app.
- **HIDDEN** = built (file evidence) but not reachable/rendered anywhere in the web UI.

> **NOTE (post-remediation):** the **HIDDEN** labels in the tables below are the ORIGINAL
> discovery snapshot. Every HIDDEN *feature/result* has since been resolved; the authoritative
> outcome is the **Remediation outcome** table immediately below. Zero presentable features
> remain hidden (verified by the information-architecture reviewer against the code,
> audit/signoffs/information-architecture.md).

## Remediation outcome (authoritative)

| Original HIDDEN item | Outcome | Where now |
|---|---|---|
| competing_risks.json | SURFACED | AI / Model Quality → "Competing risks" expander |
| fine_gray.json | SURFACED | AI / Model Quality → "Competing risks" expander |
| cblr_robustness.json | SURFACED | AI / Model Quality → "2020Q1 CBLR break" expander (chart) |
| calibration_bakeoff.json | SURFACED | AI / Model Quality → "Calibration bake-off" expander (chart) |
| b1_compare.json | SURFACED | AI / Model Quality → "Point-in-time vs restated (B1)" expander |
| maxout_experiment.json | SURFACED | AI / Model Quality → "Maxing out the model" expander (chart) |
| sequence_sweep.json | SURFACED | AI / Model Quality → GRU challenger (via sequence_challenger.robustness_sweep) |
| FAILURE_DECOMPOSITION / COMPETING_RISKS / B1 / SEQUENCE_CHALLENGER / VALIDATION_REPORT / RELATED_WORK docs | SURFACED | AI / Model Decisions → "Methodology write-ups" expanders |
| Great Expectations mart suite result | SURFACED | DE / Data Quality → GX suite block (20/20, per-expectation table) |
| ML serving routes (/predict-failure-risk, /predict, /predict/batch, /ready) | SURFACED | DE / Administration → service endpoint catalog |
| DE data API routes (/failures, /banks/{id}, /metrics/{series_id}) | SURFACED | DE / Administration → service endpoint catalog |
| K8s ml-serve + kind config; ml/Streamlit/api/airflow Dockerfiles; compose | SURFACED | DE / Administration → "Containerization & Kubernetes Deployment" block |
| anomaly_chart(), architecture_components_frame() | REMOVED | dead code deleted (A-005) |
| finlens_model_report.html | EXCLUDED | redundant with the embedded analysis notebook HTML (AI / Notebook) |
| FFIEC point-in-time loader (ffiec_pit.py) | EXCLUDED (code path) | its result IS surfaced via b1_compare; the loader is the offline code behind it |
| GX on_load / on_serve suites + checkpoints | EXCLUDED | runtime guards, not a presentable result; the mart suite result is surfaced |
| Snowflake DDL/load scripts | EXCLUDED | warehouse-target infra, not a product feature (DuckDB is the live store) |
| ABSTRACT / ARCHITECTURE / CEILING_BACKLOG / FINAL_SIGNOFF / PUBLICATION_READINESS / RUN_LOCAL / WEB_REDESIGN / PROJECT_CAPSTONES docs | EXCLUDED | engineering/process docs, not product features |
| mkdocs site, web/ static prototype | EXCLUDED | separate/ superseded builds, not part of the running Streamlit app |

Surface map (from `streamlit_app/lib/page_shell.py`):
- **Business** surface = pages `0_Stress_Pulse`, `1_Failure_Forensics`, `2_Macro_Transmission`,
  `3_Early_Warning`, `8_Analyst_Assistant`, plus the shared `6_Wiki`.
- **Data Engineering** surface = single page `4_Data_Engineering.py`, switched between 6 in-page
  sections via `st.session_state["technical_section"]`: pipeline, classification (Source
  Contracts), implementation (Engineering Stack), status (Data Quality), decisions (Architecture
  Decisions), administration.
- **AI Engineering** surface = single page `7_AI_Engineering.py`, 7 in-page sections via
  `st.session_state["ai_section"]`: pipeline, notebook, contracts, stack, quality, decisions,
  administration (+ wiki link).

---

## 1. Business UI

| Feature | Built? (file evidence) | Surfaced in UI? | Notes |
|---|---|---|---|
| Landing / home hero, 3-surface entry cards | `streamlit_app/app.py:158-210` | Home (`app.py`) | Hero + Business/DE/AI entry buttons |
| Legal-disclaimer modal (blocking) | `app.py:129-148` | Home, on first load | `@st.dialog` non-dismissible |
| Live data summary table (failures/stress/FRED/pipeline counts) | `app.py:31-67,236-242` | Home | Driven by live loaders |
| Surface summary table | `app.py:70-98,235` | Home | |
| Headline metric cards (FDIC failures, stress periods, FRED series, pipeline flows) | `app.py:215-223` | Home | |
| Stress Pulse: 4 KPI cards (net income, ROA, NIM, problem-bank count) | `pages/0_Stress_Pulse.py:418-443` | Business / Stress Pulse | Falls back to public-data snapshot if QBP empty |
| Earnings & ROA combo chart | `0_Stress_Pulse.py:51-74,452` | Business / Stress Pulse | |
| Funding (asset-yield vs cost-of-funds) chart | `0_Stress_Pulse.py:77-92,454-455` | Business / Stress Pulse | Falls back to NIM chart if split unavailable |
| Net interest margin chart | `0_Stress_Pulse.py:94-113,457` | Business / Stress Pulse | |
| Asset-quality chart (noncurrent + NCO) | `0_Stress_Pulse.py:116-135,470` | Business / Stress Pulse | |
| Unrealized losses (AFS/HTM) chart, March-2023 annotation | `0_Stress_Pulse.py:142-175,477-478` | Business / Stress Pulse | Empty-state if source lacks fields |
| Recession bands overlay helper | `0_Stress_Pulse.py:32-41` | Business / Stress Pulse | Applied to multiple charts |
| Public-data fallback snapshot (failure timeline + macro single-series + year drill-down) | `0_Stress_Pulse.py:289-384` | Business / Stress Pulse | Active when QBP aggregate not populated |
| Failure Forensics: 4 KPI cards | `pages/1_Failure_Forensics.py:205-221` | Business / Failure Forensics | |
| Failure timeline bar chart | `1_Failure_Forensics.py:47-63` | Business / Failure Forensics | (defined; map+acquirer are the rendered pair) |
| Top-acquirers horizontal bar chart | `1_Failure_Forensics.py:66-86,256` | Business / Failure Forensics | |
| State choropleth map | `1_Failure_Forensics.py:89-127,249` | Business / Failure Forensics | |
| Year + state filters | `1_Failure_Forensics.py:228-245` | Business / Failure Forensics | |
| Paginated failure inventory table | `1_Failure_Forensics.py:130-173,270-274` | Business / Failure Forensics | 12/page pager |
| Macro Transmission: 4 KPI cards (10Y-2Y, unemployment, CPI, HPI) | `pages/2_Macro_Transmission.py:216-228` | Business / Macro Transmission | |
| Macro signal selector + native-scale detail chart | `2_Macro_Transmission.py:123-136,235-248` | Business / Macro Transmission | |
| Macro signal vs monthly FDIC failures overlay chart | `2_Macro_Transmission.py:139-170,250` | Business / Macro Transmission | dual-axis |
| Indicator board table (FRED indicators, family, latest, note) | `2_Macro_Transmission.py:96-120,262` | Business / Macro Transmission | |
| 10Y-2Y yield-curve derived series | `2_Macro_Transmission.py:68-69` | Business / Macro Transmission | computed in panel |
| Per-page "Read full article in Wiki" deep links | `page_shell.py:211-227` | every business page hero | links to wiki slug |
| Persistent top bar: surface popover + brand + credit | `page_shell.py:289-332` | every page | |
| Section tabs (one per surface) | `page_shell.py:257-287` | every page | |
| Left-rail sidebar section nav + live ET clock | `page_shell.py:109-190` | every page | `@st.fragment(run_every=1s)` clock |
| Site footer | `page_shell.py:196-208` | every page | |
| Theme system (light/dark palette, CSS injection) | `streamlit_app/lib/theme.py` | every page | `app_css`, `get_palette` |

## 2. Early Warning / live model UI (Business surface)

| Feature | Built? (file evidence) | Surfaced in UI? | Notes |
|---|---|---|---|
| Early Warning page (4 interactive tabs) | `pages/3_Early_Warning.py` | Business / Early Warning | st.tabs, live scoring |
| Tab: Backtest any bank by name | `3_Early_Warning.py:153-183` | Business / Early Warning | uses `scenario.bank_directory`, predicted vs actual |
| Tab: Failed-bank backtests | `3_Early_Warning.py:185-199` | Business / Early Warning | `scenario.held_out_failed_banks` |
| Tab: Live forward score (experimental) | `3_Early_Warning.py:201-247` | Business / Early Warning | `scenario.live_bank_directory` |
| Tab: Hypothetical what-if (CAMELS sliders) | `3_Early_Warning.py:249-267` | Business / Early Warning | `scenario.SLIDER_FEATURES` |
| Probability gauge | `ml_charts.probability_gauge` (`ml_charts.py:221`) | Business / Early Warning | per-score |
| Risk-tier badge (HIGH/ELEVATED/LOW) | `3_Early_Warning.py:53-59` | Business / Early Warning | threshold-driven |
| Per-score SHAP reason table (driver, value, effect, weight) | `3_Early_Warning.py:85-112` | Business / Early Warning | `scenario.humanize_feature` |
| Input→model→output flow strip | `3_Early_Warning.py:126-138` | Business / Early Warning | |
| Live scoring backend | `ml/finlens_ml/scenario.py` | Business / Early Warning (+Analyst Assistant) | `score_features`, `score_hypothetical`, directory builders |

## 3. Analyst Assistant (RAG chatbot UI)

| Feature | Built? (file evidence) | Surfaced in UI? | Notes |
|---|---|---|---|
| Analyst Assistant page | `pages/8_Analyst_Assistant.py` | Business / Analyst Assistant | also linked from AI page (`7_AI_Engineering.py:122`) |
| Cached example-question answers | `8_Analyst_Assistant.py:48-83`; `rag/demo_answers.json` | Analyst Assistant | instant cached path |
| Live ask box (runs RAG end-to-end) | `8_Analyst_Assistant.py:97-110` | Analyst Assistant | `rag.trace.traced_answer` |
| Cited-sources rendering (regulator doc URLs) | `8_Analyst_Assistant.py:65-68` | Analyst Assistant | |
| Live model score injected into answer | `8_Analyst_Assistant.py:59-64` | Analyst Assistant | from `rag.graph.ground_model` |
| Per-query trace caption (latency, docs, citations, $0) | `8_Analyst_Assistant.py:108-110` | Analyst Assistant | |
| "How this works" eval summary (hit@4=1.0, MRR=0.92) | `8_Analyst_Assistant.py:85-94` | Analyst Assistant | hardcoded from `rag/eval_report.json` |

## 4. Wiki (encyclopedia)

| Feature | Built? (file evidence) | Surfaced in UI? | Notes |
|---|---|---|---|
| Wiki page: one-article-per-page, section tree, search | `pages/6_Wiki.py` | Wiki (shared, reachable from every surface) | |
| Section taxonomy (6 sections, sub-groups) | `wiki_structure.py:38-129` | Wiki | Intro, Business, Architecture, Data Engineering, AI Engineering, Reference |
| Article corpus (~50+ articles merged) | base `wiki_content.py` + `wiki_extra.py` (8) + `wiki_de_articles.py` (16) + `wiki_ai_articles.py` (11) | Wiki | merged in `wiki_structure.ARTICLES`; each article is a feature |
| `[[wikilink]]` cross-links | `6_Wiki.py:33-43` | Wiki | |
| Full-text search across titles/summary/body | `6_Wiki.py:46-65` | Wiki | |
| Prev/next article navigation | `6_Wiki.py:114-121`; `wiki_structure.neighbours` | Wiki | |
| Corpus stats (articles/sections/words/read-time) | `6_Wiki.py:122-135`; `wiki_structure.stats` | Wiki | |
| Browse cards home | `6_Wiki.py:137-152` | Wiki | |

## 5. Data Engineering UI (page `4_Data_Engineering.py`)

| Feature | Built? (file evidence) | Surfaced in UI? | Notes |
|---|---|---|---|
| Live Pipeline section: 4 source KPI cards + 4 infra cards | `4_Data_Engineering.py:1169-1196` | DE / Live Pipeline | with "Live" pulse badge |
| Sankey DAG flow chart (source→bronze→silver→gold→dashboards) | `4_Data_Engineering.py:73-123,1203` | DE / Live Pipeline | status-colored |
| Pipeline status table (tool/runtime/status/rows/artifact) | `4_Data_Engineering.py:126-177,1204` | DE / Live Pipeline | |
| Interactive read-only data browser (Bronze/Silver/Intermediate/Gold, paged) | `4_Data_Engineering.py:829-914,1205` | DE / Live Pipeline | `warehouse_table_preview` |
| Reconciliation controls table | `4_Data_Engineering.py:201-242,1213` | DE / Data Quality | |
| dbt data-quality summary frame | `4_Data_Engineering.py:743-758,1219` | DE / Data Quality | `dbt_artifact_summary` |
| dbt node-level results frame | `4_Data_Engineering.py:761-775,1225` | DE / Data Quality | |
| Transformation rule catalog | `4_Data_Engineering.py:577-623,1230,1263` | DE / Data Quality & Source Contracts | |
| Source classification / activation frame | `4_Data_Engineering.py:267-327,1238` | DE / Source Contracts | |
| Warehouse inventory frame | `4_Data_Engineering.py:778-792,1243` | DE / Source Contracts | |
| Transform before/after preview | `4_Data_Engineering.py:1249-1258` | DE / Source Contracts | |
| Core DE stack / tool evidence frame | `4_Data_Engineering.py:506-574,1272` | DE / Engineering Stack | |
| Platform stack readiness frame (S3, Airflow, dbt, Terraform, Snowflake, FastAPI, Cloudflare, Postgres) | `4_Data_Engineering.py:367-503,1278` | DE / Engineering Stack | live probe-aware |
| Airflow run results frame | `4_Data_Engineering.py:917-931,1282` | DE / Engineering Stack | `airflow_run_rows` |
| Latest pipeline run ledger frame | `4_Data_Engineering.py:681-704,1288` | DE / Engineering Stack | |
| Warehouse activation checklist | `4_Data_Engineering.py:1293-1316` | DE / Engineering Stack | |
| Implementation code excerpts (4 tabs: ingestion/DAG/dbt/serving) | `4_Data_Engineering.py:626-678,1317` | DE / Engineering Stack | |
| Service endpoint catalog | `4_Data_Engineering.py:934-971,1325` | DE / Administration | lists FastAPI routes |
| Control-sync (Postgres) frame | `4_Data_Engineering.py:974-1018,1330` | DE / Administration | |
| Source freshness frame | `4_Data_Engineering.py:245-264,1335` | DE / Administration | |
| Source landing artifacts frame | `4_Data_Engineering.py:795-810,1340` | DE / Administration | |
| Anomaly chart (rows-per-run band) | `4_Data_Engineering.py:180-198` | **HIDDEN** | `anomaly_chart()` defined but never called in the page |
| Architecture-components frame | `4_Data_Engineering.py:1021-1077` | **HIDDEN** | `architecture_components_frame()` defined but never called |
| Architecture Decisions handbook (component catalog, source contracts, warehouse layers, dbt catalog, decision register, glossary, external refs) | `streamlit_app/lib/architecture_docs.py:83-665` | DE / Architecture Decisions | `render_architecture_decisions()`; 8 sub-renderers |

## 6. AI / Model UI (page `7_AI_Engineering.py`)

| Feature | Built? (file evidence) | Surfaced in UI? | Notes |
|---|---|---|---|
| Pipeline section: end-to-end narrative + served-model success banner | `7_AI_Engineering.py:133-149` | AI / Pipeline | reads `metrics_h4.final_model` |
| Live source code excerpts (labels/splits/train via `inspect.getsource`) | `7_AI_Engineering.py:56-71,150-174` | AI / Pipeline & Contracts & Administration | cannot drift from runtime |
| Executed Jupyter notebook (rendered HTML) | `7_AI_Engineering.py:176-188`; `ml/notebooks/bank_distress_analysis.html` | AI / Notebook | full EDA/eval/calibration/SHAP |
| Feature contract table (monotone direction per feature) | `7_AI_Engineering.py:190-213` | AI / Contracts | `features.MONOTONE_CONSTRAINTS` |
| SHAP importance figure | `ml_charts.shap_importance_fig` | AI / Contracts | from viz_pack |
| Feature correlation heatmap | `ml_charts.correlation_fig` | AI / Contracts | |
| ML stack table | `7_AI_Engineering.py:217-228` | AI / Stack | |
| Quality KPIs (PR-AUC, ROC-AUC, Recall@200, ECE) with bootstrap CIs | `7_AI_Engineering.py:234-258` | AI / Quality | `metrics_h4.oot_test*` |
| "Beats benchmark?" paired-bootstrap statement | `7_AI_Engineering.py:259-272` | AI / Quality | `lgbm_vs_logit_ap_diff` |
| Multi-origin rolling backtest statement | `7_AI_Engineering.py:273-285` | AI / Quality | `metrics_h4.rolling_backtest` |
| Effective-challenge ladder (monotone vs unconstrained GBM vs logit) | `7_AI_Engineering.py:286-329` | AI / Quality | `metrics_h4.challengers` |
| Ablation forest figure | `ml_charts.ablation_forest_fig`; `7_AI_Engineering.py:332-333` | AI / Quality | |
| Hyperparameter-tuning summary (Optuna) | `7_AI_Engineering.py:334-341` | AI / Quality | `metrics_h4.hyperparameter_tuning` |
| Tuning auditability: optimism, Optuna history/importance/slice, trial stability | `7_AI_Engineering.py:342-366`; `ml_charts.optimism_fig/optuna_*_fig/trial_stability_fig` | AI / Quality | from `viz_pack.study` |
| G0 interval-coverage + gate-power statement | `7_AI_Engineering.py:367-391` | AI / Quality | from `viz_pack.g0` (g0_power_sim baked in) |
| PR curve / ROC curve / calibration / score-distribution / threshold figures | `7_AI_Engineering.py:392-402`; `ml_charts.pr_curve_fig`/`roc_curve_fig`/`calibration_fig`/`score_dist_fig`/`threshold_fig` | AI / Quality | |
| Capacity curve figure | `7_AI_Engineering.py:405-408`; `ml_charts.capacity_curve_fig` | AI / Quality | |
| Multi-horizon PR overlay | `7_AI_Engineering.py:409-411`; `ml_charts.multi_horizon_pr_fig` | AI / Quality | |
| By-year breakdown figure + counts | `7_AI_Engineering.py:413-424`; `ml_charts.by_year_fig` | AI / Quality | |
| Failure-type decomposition (mix-by-year + addressable-PR figures + narrative) | `7_AI_Engineering.py:426-469`; `ml_charts.load_decomposition/failure_mix_by_year_fig/addressable_pr_fig`; `ml/artifacts/failure_decomposition.json` | AI / Quality | |
| Pooled-vs-addressable across model families | `7_AI_Engineering.py:471-496`; `ml_charts.load_pooled_vs_addressable/pooled_vs_addressable_fig`; `ml/artifacts/pooled_vs_addressable.json` | AI / Quality | |
| GRU sequence challenger comparison + robustness sweep | `7_AI_Engineering.py:498-528`; `ml_charts.load_sequence/sequence_vs_gbm_fig`; `ml/artifacts/sequence_challenger.json` | AI / Quality | sweep shown via `robustness_sweep` nested in sequence_challenger |
| Drift monitoring (Evidently) + PSI figures | `7_AI_Engineering.py:530-551`; `ml_charts.drift_fig/psi_fig` | AI / Quality | from `viz_pack.drift_*` |
| Model decisions narrative + full model card | `7_AI_Engineering.py:553-576`; `docs/ml/MODEL_CARD.md` | AI / Decisions | model card embedded |
| Administration: registry/promotion/retrain/rollback + champion code | `7_AI_Engineering.py:578-590`; `finlens_ml/registry.py` | AI / Administration | |
| Research write-up (PAPER.md) popover | `7_AI_Engineering.py:125-128`; `docs/ml/PAPER.md` | AI surface (popover, all sections) | only doc besides MODEL_CARD embedded in UI |

## 7. AI / Model — backend, artifacts, scripts

| Feature | Built? (file evidence) | Surfaced in UI? | Notes |
|---|---|---|---|
| Trained calibrated model artifact | `ml/artifacts/calibrated_h4.skops`, `booster_h4.txt` | Indirectly (drives Early Warning + AI metrics) | gate for Early Warning page |
| `metrics_h4.json` (OOT metrics, CIs, challengers, tuning, rolling backtest, capacity, calibration, final_model) | `ml/artifacts/metrics_h4.json` | AI / Quality + Pipeline; Early Warning live tab caption | heavily surfaced |
| `viz_pack.json` (curves, calibration, SHAP, correlation, PSI, ablation, by_year, capacity, study, g0, drift) | `ml/artifacts/viz_pack.json` | AI / Quality + Contracts | primary AI viz source |
| `failure_decomposition.json` | `ml/artifacts/failure_decomposition.json` | AI / Quality | |
| `pooled_vs_addressable.json` | `ml/artifacts/pooled_vs_addressable.json` | AI / Quality | |
| `sequence_challenger.json` | `ml/artifacts/sequence_challenger.json` | AI / Quality | |
| `sequence_sweep.json` | `ml/artifacts/sequence_sweep.json` | **HIDDEN** | standalone file not loaded by UI; sweep numbers reach UI only via `sequence_challenger.robustness_sweep` |
| `g0_power_sim.json` | `ml/artifacts/g0_power_sim.json` | Surfaced indirectly | numbers baked into `viz_pack.g0`; standalone file not read by UI |
| `drift_report.json` | `ml/artifacts/drift_report.json` | Surfaced indirectly | numbers baked into `viz_pack.drift_*`; standalone file not read by UI |
| `competing_risks.json` (cumulative incidence, informative censoring) | `ml/artifacts/competing_risks.json`; `ml/scripts/competing_risks.py` | **HIDDEN** | only in `docs/ml/COMPETING_RISKS.md`, never in UI |
| `fine_gray.json` (cause-specific vs Fine-Gray subdistribution) | `ml/artifacts/fine_gray.json`; `ml/scripts/fine_gray.py` | **HIDDEN** | not referenced anywhere in `streamlit_app/` |
| `cblr_robustness.json` (2020 CBLR reporting-break robustness) | `ml/artifacts/cblr_robustness.json`; `ml/scripts/cblr_robustness.py` | **HIDDEN** | referenced by RAG corpus + docs, not rendered in UI |
| `calibration_bakeoff.json` (calibration method bake-off + conformal feasibility) | `ml/artifacts/calibration_bakeoff.json`; `ml/scripts/calibration_conformal.py` | **HIDDEN** | not in UI |
| `b1_compare.json` (FFIEC point-in-time vs FDIC-restated, noncurrent reconstruction) | `ml/artifacts/b1_compare.json`; `ml/scripts/b1_*.py`; `finlens_ml/ffiec_pit.py` | **HIDDEN** | only in `docs/ml/B1_POINT_IN_TIME.md` |
| `maxout_experiment.json` (44KB max-out sweep) | `ml/artifacts/maxout_experiment.json`; `ml/scripts/maxout_experiment.py` | **HIDDEN** | not referenced in UI |
| `finlens_model_report.html` (generated model report) | `ml/artifacts/finlens_model_report.html`; `ml/scripts/generate_report.py` | **HIDDEN** | not embedded anywhere (Notebook HTML is the embedded one) |
| Discrete-time hazard model training | `finlens_ml/train.py` | Code shown in AI / Pipeline | `_fit_calibrated` via getsource |
| Feature engineering (levels, trends, peer z-scores) | `finlens_ml/features.py` | Code shown in AI / Contracts | |
| Labelling + leakage control | `finlens_ml/labels.py` | Code shown in AI / Pipeline | |
| Rolling-origin OOT split + embargo | `finlens_ml/splits.py` | Code shown in AI / Pipeline | |
| Evaluation (PR/ROC/calibration/bootstrap) | `finlens_ml/evaluate.py` | Outputs surfaced (metrics) | code itself not shown |
| SHAP explainability | `finlens_ml/explain.py` | Outputs surfaced (reason tables, importance) | |
| Model card generator | `finlens_ml/model_card.py` | Output (MODEL_CARD.md) surfaced | |
| MLflow registry / champion-challenger | `finlens_ml/registry.py` | Code shown in AI / Administration | |
| Evidently drift monitor | `finlens_ml/monitor.py` | Outputs surfaced (drift section) | code itself not shown |
| Prediction service module | `finlens_ml/predict.py` | Indirect | |
| Scenario scoring backend | `finlens_ml/scenario.py` | Drives Early Warning | |
| FFIEC point-in-time loader | `finlens_ml/ffiec_pit.py` | **HIDDEN** | B1 work; not in UI |
| Failure-cause labels (regulator-sourced) | `finlens_ml/failure_cause_labels.py` | Indirect (feeds RAG + decomposition) | |
| Ensemble / bagging | `finlens_ml/ensemble.py` | Indirect (bagged_k in metrics) | |
| `$0`/no-billable-import guard | `finlens_ml/audit.py`; `ml/tests/test_no_billable_imports.py` | Mentioned in AI / Administration copy | enforced in CI |
| FastAPI model serving (`/predict`, `/predict-failure-risk`, `/predict/batch`, `/health`, `/ready`) | `finlens_ml/serve.py:111-165` | **HIDDEN** | model-serving API; not the same as DE FastAPI; routes not invoked from UI |

## 8. RAG chatbot (backend)

| Feature | Built? (file evidence) | Surfaced in UI? | Notes |
|---|---|---|---|
| LangGraph retrieve→ground→synthesize pipeline | `rag/graph.py` | Analyst Assistant (live ask) | |
| Chroma + sentence-transformers (all-MiniLM-L6-v2) retrieval | `rag/graph.py:40-81` | Analyst Assistant | |
| Live-model grounding (per-bank score injection) | `rag/graph.py:81-103` | Analyst Assistant | |
| Local Ollama synthesis (CLI + HTTP) with extractive fallback | `rag/graph.py:125-172` | Analyst Assistant | fallback used when no LLM |
| Corpus ingest (regulator failure docs + methodology docs) | `rag/ingest.py` | Indirect (powers retrieval) | FDIC OIG/OCC/Fed/Treasury OIG + method docs |
| Per-query tracing (latency/citations/cost) | `rag/trace.py` | Analyst Assistant (trace caption) | writes `traces.jsonl` |
| RAG eval harness (hit@k, MRR, citation grounding) | `rag/eval.py`; `rag/eval_report.json` | Stats surfaced in "How this works" | RAGAS LLM metrics skipped (no judge) |
| Demo answer cache | `rag/demo_answers.json` | Analyst Assistant | instant example answers |

## 9. Serving / Deploy / Infra

| Feature | Built? (file evidence) | Surfaced in UI? | Notes |
|---|---|---|---|
| DE FastAPI app (health/healthz) | `api/main.py` | Endpoints listed in DE / Administration | not invoked live from UI |
| `/failures`, `/banks/{id}` routes | `api/routers/failures.py` | **HIDDEN** | endpoints exist, not listed in DE service catalog or called |
| `/metrics/{series_id}` route | `api/routers/metrics.py` | **HIDDEN** | not listed in service catalog |
| `/telemetry/events`, `/telemetry/summary` routes | `api/routers/telemetry.py` | Listed in DE / Administration | telemetry intake/summary |
| Telemetry recording (page views) | `streamlit_app/lib/telemetry.py`; `finlens/telemetry.py` | Runs on every page (background) | feeds control-sync frame |
| dbt staging models (FDIC failures, QBP, FRED, NIC) | `dbt/models/staging/*.sql` | Surfaced as catalog rows (DE) + data browser | |
| dbt marts: `fct_bank_failures`, `fct_financial_metrics`, `fct_stress_pulse` | `dbt/models/marts/*.sql` | Data browser + catalog | drive business pages |
| dbt mart: `bank_quarterly_risk_facts` (per-bank-quarter CAMELS risk facts) | `dbt/models/marts/bank_quarterly_risk_facts.sql` | Data browser (if built) + DE catalog | Capstone-1 gold mart; grain (cert, quarter) |
| dbt intermediate / reference / snapshot models | `dbt/models/intermediate`,`/reference`,`/snapshots` | Data browser + catalog | SCD snapshot `dim_bank_snapshot` |
| dbt schema tests + custom uniqueness test | `dbt/models/marts/schema.yml`; `dbt/tests/assert_*` | dbt results frame (DE / Data Quality) | |
| Great Expectations suite — `bank_quarterly_risk_facts` (20 expectations) | `great_expectations/expectations/bank_quarterly_risk_facts.json` | **HIDDEN** | GX results not rendered; only dbt quality is surfaced |
| Great Expectations suites — on_load (2), on_serve (1) + checkpoints + validate.py | `great_expectations/` | **HIDDEN** | checkpoint/validation outputs not surfaced in UI |
| Airflow DAGs (7): ingest fdic/fred/nic/qbp, transform_and_quality, ml_retrain, sync_control_plane | `airflow/dags/*.py` | Status surfaced as rows (DE Airflow run results) | DAG bodies not shown except code excerpt |
| K8s ML-serve manifest + kind config | `deploy/k8s/ml-serve.yaml`,`kind-config.yaml` | **HIDDEN** | infra artifact, not surfaced |
| ML Dockerfile + Streamlit/airflow/api Dockerfiles + compose | `ml/Dockerfile`, `Dockerfile.streamlit`, `docker-compose.prod.yml`, `airflow/docker-compose.yml` | **HIDDEN** | infra |
| Terraform (S3 buckets module, providers, vars) | `terraform/` | Status row in DE platform stack | code not shown |
| Snowflake DDL + load scripts | `snowflake/ddl/*`, `snowflake/load/*` | **HIDDEN** | warehouse target, not surfaced |
| DuckDB DDL + mart export | `duckdb/ddl`, `duckdb/export_marts.py` | Indirect (powers data browser) | |
| Ingestion connectors (fdic, fdic_institutions, fred, nic, qbp) | `ingestion/*.py` | Status + code excerpt (DE) | |
| Platform probes / pipeline-run ledger / state store | `src/finlens/platform_probes.py`,`pipeline_runs.py`,`state.py` | DE / Engineering Stack frames | |
| Postgres control-plane sync script | `scripts/sync_control_plane_to_postgres.py` | Status in DE / Administration | |
| Local pipeline runner / dbt build runner / airflow evidence collector | `scripts/run_local_pipeline.py`,`run_dbt_build.py`,`collect_airflow_evidence.py` | Outputs surfaced as DE frames | |

## 10. Docs / Paper

| Feature | Built? (file evidence) | Surfaced in UI? | Notes |
|---|---|---|---|
| `PAPER.md` (measurement paper) | `docs/ml/PAPER.md` | AI surface popover (`7_AI_Engineering.py:125-128`) | only narrative doc surfaced live besides model card |
| `MODEL_CARD.md` | `docs/ml/MODEL_CARD.md` | AI / Decisions expander | embedded |
| `FAILURE_DECOMPOSITION.md` | `docs/ml/FAILURE_DECOMPOSITION.md` | **HIDDEN** | content paraphrased in AI/Quality; doc itself not linked |
| `COMPETING_RISKS.md` | `docs/ml/COMPETING_RISKS.md` | **HIDDEN** | |
| `SEQUENCE_CHALLENGER.md` | `docs/ml/SEQUENCE_CHALLENGER.md` | **HIDDEN** | |
| `B1_POINT_IN_TIME.md` | `docs/ml/B1_POINT_IN_TIME.md` | **HIDDEN** | |
| `VALIDATION_REPORT.md` | `docs/ml/VALIDATION_REPORT.md` | **HIDDEN** | |
| `RELATED_WORK.md` | `docs/ml/RELATED_WORK.md` | **HIDDEN** | |
| `ABSTRACT.md`, `ARCHITECTURE.md`, `CEILING_BACKLOG.md`, `FINAL_SIGNOFF.md`, `PUBLICATION_READINESS.md`, `RUN_LOCAL.md`, `WEB_REDESIGN.md` | `docs/ml/*.md` | **HIDDEN** | engineering/process docs, not linked in UI |
| `PROJECT_CAPSTONES.md` | `docs/PROJECT_CAPSTONES.md` | **HIDDEN** | |
| Architecture docs, ADRs (0001-0008), data-flow/model, operations, secrets, validation | `docs/architecture/*`, `docs/adr/*`, `docs/*.md` | Partly mirrored in DE/Architecture Decisions handbook (own copy) | source `.md` files not rendered; DE handbook is hand-built |
| MkDocs site config | `mkdocs.yml` | **HIDDEN** | separate static-site build, not in Streamlit |
| Standalone static web prototype | `web/index.html`, `web/app.js`, `web/styles.css` | **HIDDEN** | superseded by Streamlit app; not served from it |
| Repo-level build/state docs (`BUILD_STATE.md`, `README.md`, `agents/ML_MAXOUT_PLAN.md`) | repo root / `agents/` | **HIDDEN** | process docs |

---

## Summary

Approximate totals (rows in the tables above; closely-related figures grouped):

- **Total distinct features/capabilities/artifacts catalogued:** ~150
- **Surfaced (reachable + visible in the Streamlit web UI):** ~110, across:
  - Home (`app.py`)
  - Business: Stress Pulse, Failure Forensics, Macro Transmission, Early Warning, Analyst Assistant
  - Wiki (~50 articles, 6 sections)
  - Data Engineering: 6 sections (Live Pipeline, Source Contracts, Engineering Stack, Data Quality, Architecture Decisions, Administration)
  - AI Engineering: 7 sections (Pipeline, Notebook, Feature Contracts, AI Stack, Model Quality, Model Decisions, Administration) + PAPER popover
- **Surfaced only indirectly** (numbers baked into a surfaced artifact, the standalone file/route is not itself read by the UI): `g0_power_sim.json`, `drift_report.json` (folded into `viz_pack.json`); model-serving FastAPI predictions (Early Warning uses the in-process `scenario.py`, not the HTTP routes).

### HIDDEN features (built, not reachable/visible in the web UI)

In-app code defined but never called:
1. `anomaly_chart()` — DE rows-per-run anomaly chart (`4_Data_Engineering.py:180-198`)
2. `architecture_components_frame()` — DE architecture-layer table (`4_Data_Engineering.py:1021-1077`)

ML result artifacts + their scripts, not surfaced anywhere in the UI:
3. `competing_risks.json` + `ml/scripts/competing_risks.py` (docs only)
4. `fine_gray.json` + `ml/scripts/fine_gray.py`
5. `cblr_robustness.json` + `ml/scripts/cblr_robustness.py` (in RAG corpus, not UI)
6. `calibration_bakeoff.json` + `ml/scripts/calibration_conformal.py`
7. `b1_compare.json` + `ml/scripts/b1_*.py` + `finlens_ml/ffiec_pit.py`
8. `maxout_experiment.json` + `ml/scripts/maxout_experiment.py`
9. `sequence_sweep.json` (standalone; sweep reaches UI only via `sequence_challenger.robustness_sweep`)
10. `finlens_model_report.html` + `ml/scripts/generate_report.py` (generated report never embedded)

Serving / API routes not exposed in the UI:
11. Model-serving FastAPI routes `/predict`, `/predict-failure-risk`, `/predict/batch`, `/ready` (`finlens_ml/serve.py`)
12. DE FastAPI routes `/failures`, `/banks/{id}`, `/metrics/{series_id}` (not in the DE service-endpoint catalog, only telemetry + health are listed)

Quality / validation tooling not rendered:
13. Great Expectations entirely — `bank_quarterly_risk_facts` (20 expectations), `on_load`, `on_serve` suites, checkpoints, `validate.py` (only dbt quality is surfaced in DE / Data Quality)

Infra artifacts not surfaced:
14. K8s manifests (`deploy/k8s/*`), Dockerfiles + compose, Snowflake DDL/load scripts, full Terraform code (only a readiness status row appears)

Docs not linked from the UI (everything in `docs/` except PAPER.md and MODEL_CARD.md):
15. `FAILURE_DECOMPOSITION.md`, `COMPETING_RISKS.md`, `SEQUENCE_CHALLENGER.md`, `B1_POINT_IN_TIME.md`, `VALIDATION_REPORT.md`, `RELATED_WORK.md`, `ABSTRACT.md`, `ARCHITECTURE.md`, `CEILING_BACKLOG.md`, `FINAL_SIGNOFF.md`, `PUBLICATION_READINESS.md`, `RUN_LOCAL.md`, `WEB_REDESIGN.md`, `PROJECT_CAPSTONES.md`, all `docs/adr/*`, `docs/architecture/*`, `docs/*.md`, `mkdocs.yml`

Superseded prototype:
16. Standalone static `web/` prototype (`index.html`, `app.js`, `styles.css`, vendored ECharts) — not served by the Streamlit app

### Notable "almost hidden" items worth surfacing for a max-impact demo
- The **competing-risks / Fine-Gray** survival analysis and the **B1 FFIEC point-in-time** work are some of the most rigorous artifacts in the repo and are completely absent from the web UI.
- **Great Expectations** is a full data-quality suite (23 expectations across 3 suites) that a DE reviewer would look for, but the DE / Data Quality section only shows dbt outcomes.
- The **calibration bake-off** and **max-out experiment** are decision-grade evidence that never reach a viewer.
