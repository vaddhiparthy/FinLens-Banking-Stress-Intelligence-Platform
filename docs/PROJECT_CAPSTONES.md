# FullLens unified plan: three capstones + the measurement paper, one $0 project

One project, three capstone tracks plus a research output, all on the existing FinLens
bank-failure codebase, all $0 / open-source / local-first (the standing constraint; a CI
import-guard blocks billable imports). The cloud services named in the capstone brief map to
their $0 local equivalents; nothing here requires a paid account.

Guiding rule: **add, never destroy.** The existing model layer (served champion at commit
7473608) and the publication items (C1-C5, S1-S4 in PUBLICATION_READINESS.md) stay exactly as
they are. The capstones wrap around them.

## $0 substitution map (brief term -> what we actually use)

| Brief names | FullLens $0/local equivalent |
|---|---|
| AWS S3 (bronze) | local object store (MinIO optional) / versioned local parquet |
| Iceberg/Delta (silver) | DuckDB typed tables (local lakehouse) |
| Snowflake (gold) | DuckDB `ml.training_dataset` / mart tables |
| Spark transform | pandas + DuckDB SQL (data fits in memory) |
| Milvus (vector store) | Chroma, local persistent |
| Langfuse cloud | Langfuse self-host / OSS, or local trace JSONL |
| Hosted LLM API | local Ollama model (no paid API; $0) |

## Capstone 1: FullLens Data Platform (DE). Status: PARTIAL (audited)

Audit (D1) found two real gaps; both now CLOSED:
- **Gold mart built:** `dbt/models/marts/bank_quarterly_risk_facts.sql` at the (cert, quarter)
  grain, sourced from `ml.training_dataset` (same DuckDB), with grain integrity tests (not_null
  cert/quarter + a dependency-free composite-unique singular test). `dbt build` SUCCESS.
- **Real GX suite + runner:** `great_expectations/expectations/bank_quarterly_risk_facts.json`
  (GX v3 format) asserts schema (column existence), freshness (max quarter >= 2024Q4), and
  null-rate (mostly thresholds, with tier1_rwa intentionally tolerant of the ~37% CBLR null),
  run by `great_expectations/validate.py` -> 20/20 passed, exits non-zero on failure. Note:
  the real GX PyPI engine is shadowed by the repo's `great_expectations/` directory, so
  the runner is a self-contained evaluator of the same GX-format suite (documented in the file).
- Medallion layering was already documented (data-flow / data-model / ADRs).

| Component | Brief | FullLens | Status |
|---|---|---|---|
| Sources | FRED + FDIC failed-bank + Call Report | `ingestion/fred.py`, `fdic.py`, `fdic_institutions.py`, `nic.py`, `qbp.py` | EXISTS |
| Ingestion DAG | one Airflow DAG | `airflow/dags/dag_ingest_{fred,fdic,nic,qbp}.py` | EXISTS |
| Bronze/Silver/Gold | S3 -> Iceberg -> Snowflake | local raw -> DuckDB typed -> DuckDB gold (`src/finlens/storage.py`, ADR 0001) | EXISTS (verify medallion naming) |
| Transform | Spark join macro+bank, risk ratios | `dag_transform_and_quality.py` + `ml/scripts/build_dataset.py` (34 ratios) | EXISTS |
| dbt | staging + mart `bank_quarterly_risk_facts` | `dbt/` project | EXISTS (verify the named mart) |
| Quality | Great Expectations suite | `great_expectations/` + Pydantic + null/freshness checks | EXISTS (verify GX suite coverage) |
| Demo | Airflow UI + gold table + GX report | present locally | VERIFY/screenshot |

DE gaps to confirm/close: (a) the gold mart is literally named `bank_quarterly_risk_facts`;
(b) a GX suite asserts schema + freshness + null-rate on the key ratios; (c) medallion layers
are documented. These are verification/polish, not new builds.

## Capstone 2: FullLens Risk Model (ML). Status: PARTIAL (audited) + research depth

Audit (D2): the full ML stack EXISTS (train, MLflow registry+alias promotion, Evidently drift,
SHAP, calibrated served artifact) and the serving app already returns probability + SHAP.
Closed: the named `/predict-failure-risk` alias route (serve.py); `ml/Dockerfile` for the
ML-serving app (the prior container built the DE marts API, not finlens_ml.serve); and
`deploy/k8s/` (kind-config + NodePort deployment/service). These were built and run for real,
not just inspected: the image (fulllens-ml-serve:latest, 1.57GB) serves /predict-failure-risk
(probability + SHAP) as a container, and was deployed to a live kind kubernetes cluster (pod
Running 1/1, prediction served through the NodePort, then torn down). Docker v29.4.3, kind
v0.24.0, kubectl.

| Component | Brief | FullLens | Status |
|---|---|---|---|
| Input | gold table | DuckDB `ml.training_dataset` | EXISTS |
| Model | XGBoost, 4q failure, time split | served calibrated **monotone LightGBM** (bagged); **XGBoost** now in the challenger ladder; point-in-time embargoed split | EXISTS |
| Tracking | MLflow runs (AUC, P/R, importance) | `registry.py` + metrics artifacts | EXISTS |
| Registry | staging->production | MLflow champion-alias promotion + metric gate | EXISTS |
| Serving | FastAPI `/predict-failure-risk` + SHAP | `serve.py` + `explain.py` | EXISTS (verify endpoint name/shape) |
| Container | Docker -> kind | Dockerfile / compose | VERIFY |
| Monitoring | Evidently drift | `monitor.py` | EXISTS |
| Research depth | (beyond brief) | C1-C5 + S1-S4 measurement paper | IN PROGRESS |

ML gaps to confirm/close: (a) the serving route is exposed as `/predict-failure-risk`
returning probability + SHAP; (b) the Docker/kind deploy is current. The publication track is
the analytical over-delivery that distinguishes this from every other capstone.

## Capstone 3: FullLens Analyst Assistant (RAG/Agent). Status: NEW BUILD

The genuinely new track. Reuses the C1 FDIC/OIG failure-report corpus already gathered.

| Component | Plan ($0) |
|---|---|
| Knowledge base | the cited FDIC OIG / OCC / Fed failure reports from `failure_cause_labels.py` + SR/FDIC regulatory docs + Capstone-2 model outputs |
| Vector store | Chroma, local persistent (`rag/` package) |
| RAG path | "Why did SVB fail?" / "risk factors for bank X this quarter?" -> retrieve docs + pull live model prediction from Capstone 2 -> LangGraph synthesis -> cited answer |
| LLM | local Ollama (open-source model), no paid API |
| Eval | RAGAS (faithfulness, context precision, answer relevance) on a 20-question set |
| Observability | Langfuse self-host (or local trace JSONL): cost/query, latency, retrieval quality |
| Demo | chatbot surface (4th Streamlit page) + RAGAS report + trace dashboard |

Build order for C3: (1) `rag/ingest.py` builds the Chroma index from the failure-report
corpus; (2) `rag/graph.py` LangGraph retrieve->model-fetch->synthesize with citations;
(3) `rag/eval.py` RAGAS on a 20-Q set; (4) Langfuse/local tracing; (5) a Streamlit
"Analyst Assistant" page. Each gated.

## Consolidated checklist (master)

Publication track (see PUBLICATION_READINESS.md): C1 done; C2/C3/C5 in progress; C4 in
progress; S1-S4 pending; V0 partial.

Capstone track (this doc):
- [ ] D1 verify/close Capstone-1 gaps (mart name, GX suite, medallion docs)
- [ ] D2 verify/close Capstone-2 gaps (`/predict-failure-risk` route, Docker/kind)
- [ ] R1 RAG ingest -> Chroma index from the failure-report corpus
- [ ] R2 LangGraph RAG path (retrieve + model-fetch + cited synthesis, local LLM)
- [ ] R3 RAGAS 20-Q eval
- [ ] R4 Langfuse/local observability
- [ ] R5 Analyst Assistant Streamlit page + demo

## Validation

Every capstone item uses the same per-item adversarial gate as the publication items: three
parallel reviewers (methodologist, domain, reproducibility/honesty), unanimous pass with zero
blockers, then commit. RAG items add a faithfulness/citation check (no uncited claims; answers
grounded in retrieved docs).

## Scope notes

- $0 is non-negotiable; every paid service is substituted with a local/OSS equivalent above.
- The 66-out-of-time-failure wall still bounds the *model/paper* tier; it does not affect the
  DE or RAG tracks, which are engineering deliverables.
- Capstones 1 and 2 are demonstrations of already-built infrastructure; the new engineering
  effort is concentrated in Capstone 3 (RAG) and the publication track.
