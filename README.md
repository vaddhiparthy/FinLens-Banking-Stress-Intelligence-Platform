# FinLens — Banking Stress Intelligence Platform

FinLens is an end-to-end banking stress intelligence platform that turns free public data from the FDIC, FFIEC, and Federal Reserve into a calibrated, explainable early-warning read on U.S. bank distress. It covers the full stack: automated ingestion of four official regulatory feeds, a medallion data model built on DuckDB and dbt, a discrete-time hazard model that produces a 4-quarter distress probability for every FDIC-insured institution, and four analyst-facing Streamlit surfaces backed by a FastAPI service and a retrieval-augmented assistant — all orchestrated with Airflow and gated by layered data quality checks.

**Live:** [surya.vaddhiparthy.com/FinLens-Banking-Stress-Intelligence-Platform](https://surya.vaddhiparthy.com/FinLens-Banking-Stress-Intelligence-Platform/)

**Portfolio:** [surya.vaddhiparthy.com](https://surya.vaddhiparthy.com/) &nbsp;|&nbsp; [Data Platforms](https://surya.vaddhiparthy.com/data-platforms)

---

## What It Does

| Layer | Description |
|---|---|
| Ingestion | Python clients pull FDIC BankFind + Failed Bank List, FDIC Quarterly Banking Profile, FRED/ALFRED macro series (point-in-time aware via ALFRED), and FFIEC NIC institution metadata. Retry, watermarks, and dead-letter queuing are built in. |
| Bronze | Raw payloads land verbatim on the local filesystem, Hive-partitioned by source and ingestion date. Immutable and replayable. A rotation policy retains exactly one version per source. |
| Silver / Intermediate / Gold | dbt models on DuckDB normalize raw payloads (Silver), build reusable joins (Intermediate), and produce the stable consumption contract (Gold facts and dimensions). Nothing in the serving layer reads below Gold. |
| Quality | Great Expectations suites guard raw ingestion and the Gold serving layer. dbt tests enforce structural contracts. Runtime reconciliation checks against external authority. |
| ML | A calibrated, monotone-constrained, 12-seed bagged LightGBM discrete-time hazard model scores each bank-quarter's probability of failing within 4 quarters. Trained on 448,661 bank-quarters across ~8,800 institutions (2008Q1–2026Q1), evaluated out-of-time on the last 28 quarters (118,943 bank-quarters, 66 real failures). Out-of-time PR-AUC 0.301 (95% CI [0.191, 0.438]), ROC-AUC 0.855, recall@200 0.545. Explained with SHAP; top drivers are tier-1 capital ratio and noncurrent loan ratio, consistent with the bank-failure literature. |
| Serving | Four Streamlit surfaces (Business, Data Engineering, AI Engineering, Wiki). FastAPI health, telemetry, and scoring endpoints. A retrieval-augmented assistant that retrieves cited regulator filings and live model scores, synthesizes with an LLM, and falls back to a fully-cited extractive answer. |
| Orchestration | Airflow thin DAGs schedule ingestion and transforms using the same Python entry points used locally — no orchestrator-only code path. |

---

## Architecture

```
Public data sources (FDIC BankFind · Failed Bank List · FDIC QBP · FRED/ALFRED · FFIEC NIC)
  → Python ingestion clients (retry · watermarks · dead-letter queue)
  → Immutable Bronze on local filesystem (Hive-partitioned, rotation policy)
  → dbt Silver → Intermediate → Gold on DuckDB
  → Great Expectations + dbt tests (quality gates at every boundary)
  → Discrete-time hazard model (calibrated · monotone · 12-seed bagged LightGBM)
      → SHAP attributions · OOT metrics · chart artifacts
  → Streamlit surfaces (Business · Data Engineering · AI Engineering · Wiki)
  → FastAPI (health · telemetry · scoring endpoints)
  → RAG assistant (retrieval + cited answers · LLM synthesis)
  Orchestration: Airflow DAGs
```

---

## Model Performance

Metrics are from real out-of-time evaluation (test window: 2019–2026, 66 real bank failures). PR-AUC is the lead metric at a sub-1% base rate; accuracy is not reported.

| Model | PR-AUC | ROC-AUC | recall@200 | Brier |
|---|---|---|---|---|
| Calibrated LGBM (served) | **0.301** | 0.855 | 0.545 | 0.00045 |
| Unconstrained GBM | 0.270 | 0.833 | 0.515 | 0.00045 |
| Logit benchmark | 0.153 | 0.924 | 0.379 | 0.00874 |

95% percentile-bootstrap CIs: PR-AUC [0.191, 0.438], recall@k [0.419, 0.657]. The LightGBM model's PR-AUC advantage over the logit benchmark has a paired-bootstrap P(LGBM > logit) of 100%. Top SHAP drivers: tier-1 capital ratio, noncurrent-to-loans ratio, ROE, leverage, and equity-to-assets — all consistent with CAMELS-based failure literature.

Calibration: ECE 1.22e-04; in the top-scoring decile the model predicts 0.0035 vs observed 0.0035.

---

## Tech Stack

| Layer | Tools |
|---|---|
| Language | Python 3.11+, SQL |
| Ingestion | FDIC BankFind, FDIC QBP, FRED/ALFRED, FFIEC NIC (custom clients) |
| Transformation | dbt-core, dbt-duckdb, DuckDB |
| Quality | Great Expectations, dbt tests |
| Orchestration | Airflow |
| ML | LightGBM, scikit-learn, SHAP, MLflow, Optuna, skops, Evidently |
| Serving | Streamlit, FastAPI, Uvicorn |
| API / Utils | Pydantic, structlog, tenacity, Plotly, Pandas |
| Optional warehouse | Snowflake (credential-gated; not the live path) |

---

## Repository Layout

| Path | Purpose |
|---|---|
| `ingestion/` | Per-source ingestion clients |
| `src/finlens/` | Shared config, state, telemetry, storage, and warehouse helpers |
| `dbt/` | Staging, intermediate, mart, and reference models |
| `airflow/` | DAGs and orchestration support |
| `great_expectations/` | Source and serving quality suites |
| `duckdb/` | Local mart DDL and export utilities |
| `api/` | FastAPI health, metrics, and telemetry endpoints |
| `streamlit_app/` | Business, Data Engineering, AI Engineering, and Wiki surfaces |
| `ml/` | Training pipeline, evaluation, SHAP, MLflow artifacts |
| `scripts/` | Pipeline and operational scripts |
| `docs/` | Architecture, data model, validation, ML model card, and ADRs |
| `tests/` | Unit and smoke coverage |

---

## Quickstart

Runs locally on CPU with free public data ($0, no cloud). Requires Python 3.11–3.13 and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/vaddhiparthy/FinLens-Banking-Stress-Intelligence-Platform.git
cd FinLens-Banking-Stress-Intelligence-Platform

# install runtime + ML + dev deps
uv sync --extra ml --group dev

# run the website (Business / Data Engineering / AI Engineering / Wiki surfaces)
uv run streamlit run streamlit_app/app.py
```

Optional ML pipeline (builds the dataset from real FDIC data, trains, and serves):

```bash
uv run python ml/scripts/build_dataset.py --start 2008Q1   # ~448k bank-quarters into .duckdb
uv run python ml/finlens_ml/train.py --horizon 4           # OOT eval + artifacts in ml/artifacts/
uv run uvicorn finlens_ml.serve:app --port 8077            # FastAPI scoring (/health, /predict)
```

Run the tests with `uv run pytest -q`. The full multi-service topology (Streamlit, FastAPI,
Postgres, Airflow) is defined in `docker-compose.prod.yml`; it targets the production VPS
(external networks and vault-mounted secrets) and is not meant to be run as-is locally. See
[docs/ml/RUN_LOCAL.md](docs/ml/RUN_LOCAL.md) for the detailed end-to-end ML walkthrough.

---

## License

This project is proprietary. All rights reserved. No use, copying, modification, distribution, or commercial use is permitted without the author's prior written authorization. See [LICENSE](LICENSE).

---

**Author:** Sri Surya S. Vaddhiparthy
