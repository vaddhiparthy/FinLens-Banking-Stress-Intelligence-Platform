# FinLens — Production Architecture (Gate 1)

Status: DRAFT — pending 30-yr adversarial architect sign-off at 100%.
Question this gate answers: **Does the ML inference pipeline (and the DE pipeline behind it)
authentically reflect what a real large-bank (e.g., JPMorgan Chase) MLE/DE team runs in
production — faithfully mapped to a $0 budget on a single modest VPS?** If not, redo.

Two parts: A) the presentation information-architecture (for the later UI gate, recorded
here for traceability); B) the production system architecture (the focus of THIS gate).

---

## Part A — Presentation IA (built in the UI phase, not this gate)
- **Home**: disclaimer + brief project intro + clean links to the three verticals.
- **Verticals** (persistent surface-switch across all; clean tabbed menu within each):
  - **Business** — Stress Pulse, Failure Forensics, Macro Transmission (+ their visualizations).
  - **Data Engineering** — live pipeline/run status, source contracts, medallion layers, data
    quality (GX), lineage, stack, ADRs. Deep-links → DE Architecture tab.
  - **Machine Learning** — model overview, performance, calibration, SHAP, drift, governance,
    and the Live Stress Lab. Deep-links → ML Architecture tab.
- **Wiki** — separate top-level switch (not a vertical): in-depth theory.
- **Architect's Desk** — separate top-level surface: a **home** with an interactive end-to-end
  flow map (DAG of sources → ingestion → medallion → features → model → serving → monitoring →
  surfaces; clickable nodes → component detail pages) + two tabs: **DE Architecture**, **ML
  Architecture**.

---

## Part B — Production system architecture (THIS GATE)

### B.0 Design stance
Mirror real large-bank production *patterns and component boundaries* exactly; implement each
with a free/OSS counterpart that runs on one CPU VPS at $0. Every component is labelled:
**[LIVE]** implemented & running · **[LOCAL]** implemented, runs locally/VPS · **[SCAFFOLD]**
defined as code/config but not exercised · **[REFERENCE]** the cloud-grade equivalent named for
fidelity, intentionally not built. No component is claimed beyond its label.

### B.1 The Chase-grade reference ML inference pipeline (what we are mirroring)
A real bank distress/credit model serving stack typically has:
1. **Sources & ingestion** — regulatory/market feeds → raw landing (object store), schema-checked.
2. **Batch + streaming feature pipelines** — point-in-time-correct feature computation.
3. **Feature store** — offline (training) + online (low-latency serving), train/serve parity.
4. **Training pipeline** — orchestrated, reproducible, experiment-tracked.
5. **Model registry** — versioned, stage/alias, lineage to data + code.
6. **Validation/MRM gate** — SR 11-7/26-2: conceptual soundness, OOT backtest, calibration,
    bias/segment, effective challenge; sign-off before promotion.
7. **Serving** — real-time low-latency API + batch scoring; champion/challenger; shadow/canary.
8. **Inference-time feature retrieval** — pull online features by key; request/response logging.
9. **Monitoring** — data drift, prediction drift, performance, calibration, SLAs; alerting.
10. **Retraining loop** — scheduled + drift-triggered; rollback via alias repoint.
11. **Governance/lineage/audit** — model inventory, data lineage, immutable audit trail.
12. **CI/CD** — code + data + model gates; manual promotion to champion.

### B.2 The $0 / single-VPS mapping (component-by-component, honestly labelled)
| # | Production component | Chase-grade tool (reference) | FinLens $0 counterpart | Label |
|---|---|---|---|---|
| 1 | Raw ingestion / landing | Kafka + S3 data lake | FDIC BankFind + FRED/ALFRED APIs (free) → local raw JSON; S3 mirror optional-OFF | LIVE |
| 2 | Batch feature pipeline (PIT) | Spark + dbt | DuckDB + dbt + `finlens_ml.features` (PIT, embargo) | LOCAL |
| 2b| Streaming features | Flink/Spark Structured Streaming | not needed (quarterly cadence) — REFERENCE; quarterly batch is the correct cadence | REFERENCE |
| 3 | Feature store (online/offline) | Tecton / Feast (Redis online) | offline = DuckDB point-in-time snapshots; online = the bank-quarter row served by `scenario.py`/API. Single quarterly model → a full feature store is overkill (documented tradeoff) | LOCAL / REFERENCE |
| 4 | Training pipeline | Kubeflow/SageMaker Pipelines | `finlens_ml.train` as an Airflow task; seeds + pinned deps | LOCAL |
| 5 | Model registry | SageMaker/MLflow registry | MLflow 3.x, **aliases** (champion), Postgres/sqlite backend; **serving resolves `models:/name@champion`** (`predict._registry_load`) so an alias repoint is a real serve-time rollback, with the pinned local artifact as offline fallback | LOCAL |
| 6 | Validation / MRM | internal MRM platform | model card + validation report (SR 11-7 three pillars) + CI metric gate | LOCAL |
| 7 | Real-time serving | SageMaker endpoint / KServe | FastAPI (`finlens_ml.serve:app`) lifespan-loaded, calibrated prob + SHAP, /predict + /batch + /health + /ready. **Runs via `uvicorn finlens_ml.serve:app`; NOT yet wired into the deployed `api/` container** (that container serves DE marts only) | LOCAL |
| 7b| Champion/challenger + shadow | traffic router | alias mechanism exists (champion); no challenger registered, no shadow router at this scale | REFERENCE |
| 8 | Inference feature retrieval + logging | online store + req/resp log | feature lookup from the panel by CERT; **req/resp + reason-code + version audit log** (`audit.py` JSONL, wired into `serve._score_one`/`predict_batch`, returns `request_id`) | LOCAL |
| 9 | Monitoring | Evidently/Arize/Fiddler | Evidently 0.7.x drift + prediction-drift report; health/ready; can read the inference log | LOCAL |
| 10| Retraining loop | scheduled + drift trigger | Airflow quarterly DAG `dag_ml_retrain` (build→train+register→metric gate→export); gate blocks promotion | LOCAL |
| 11| Governance / lineage / audit | Collibra / Unity Catalog | model inventory + data lineage docs; MLflow run→git SHA→data snapshot | LOCAL |
| 12| CI/CD | Jenkins/GH Actions + model gates | GitHub Actions `ml.yml`: cost-guard + suite + metric gate | LIVE (CI defined) |

### B.3 DE pipeline (medallion) — what a bank DE team runs, $0-mapped
Sources (FDIC, FRED, QBP, NIC) → **bronze** raw artifacts → **silver** staging (dbt) →
**intermediate** business logic (dbt) → **gold** marts (dbt) → consumers (Streamlit/FastAPI/web).
Orchestration: Airflow DAGs (ingest per source, transform+quality, control-plane sync).
Quality: Great Expectations checkpoints on load + on serve. Warehouse: DuckDB (local) / Postgres
(control plane); Snowflake DDL is the cloud-target [REFERENCE]. Lineage: dbt graph + source
contracts. This already exists in `airflow/`, `dbt/`, `great_expectations/`, `duckdb/`.

### B.4 Honesty constraints the architect must enforce
- No component claimed above its label. SCAFFOLD/REFERENCE clearly distinguished from LIVE/LOCAL.
- $0 invariant holds (CI import-guard forbids ML→billable services).
- The quarterly cadence is the *correct* design for Call-Report data — not a shortcut; streaming/
  online-store omission is a justified tradeoff, not a gap, and is labelled REFERENCE.
- Where the $0 mapping genuinely diverges from a bank (e.g., no real online store, no live A/B
  router), it is stated as a deliberate scale tradeoff, not hidden.

### B.5 Open questions for the architect
1. Is the component set complete vs a real bank distress/credit serving stack, or is something
   material missing (e.g., feature lineage at inference, reason-code logging, model inventory)?
2. Are the LIVE/LOCAL/SCAFFOLD/REFERENCE labels honest and the tradeoffs defensible at $0?
3. What must move from SCAFFOLD→LOCAL to make this a credible "production-shaped" pipeline a Chase
   MLE would recognize (e.g., request/response logging, retraining DAG, champion/challenger)?
