# FinLens ML Subsystem: Architecture (v1, for architect review)

Status: SIGNED OFF, adversarial architect review 100/100 (2 rejections resolved). Cleared to build P1.
Branch: `machine-learning-portfolio`
Deploy target (now): **local** (full stack runs on workstation). VPS deploy deferred to explicit approval.

## 0.0 Hard global constraints (non-negotiable, reviewer must enforce)

1. **$0 cost. Zero money-touching.** No paid APIs, no new cloud spend, no billable activity on the VPS. FDIC +
   FRED data are free/no-key. All libraries OSS (LightGBM, MLflow, FastAPI, Evidently, scikit-learn, DuckDB,
   Postgres). The ML subsystem writes **nothing to AWS S3 / Snowflake / any billable service**, it must not add a
   single PUT/credit. It reuses the resources already running on the VPS; no new paid instance, volume, or managed
   service.
2. **Total visibility, nothing invisible.** Every layer (ingestion → panel → features → splits → model → calibration
   → evaluation → explainability → serving → monitoring → governance) must be inspectable in the UI. No black boxes:
   the user can see the data, the SQL, the feature definitions, the split logic, the metrics from real runs, the SHAP
   drivers, the model card, and the live serving/monitoring state.
3. **Efficient reuse of existing VPS resources.** Bounded memory, `OMP_NUM_THREADS=1`, no GPU, coexist with Airflow/
   DuckDB/Postgres/FastAPI/Streamlit already running. Lightweight by design.

## 0.1 Site information architecture: grounded in the REAL current structure

Current site (verified in `streamlit_app/app.py` `_surface_summary` and `streamlit_app/lib/page_shell.py`) has **two
surfaces**:
- **Business surface** (`BUSINESS_PAGE`): Stress Pulse (`pages/0`), Failure Forensics (`pages/1`), Macro Transmission
  (`pages/2`), Predictive Analytics (`pages/3_Predictive_Analytics.py`, currently "coming soon"), Wiki (`pages/6`).
- **Technical surface** (`TECHNICAL_PAGE`, all rendered inside `pages/4_Under_The_Hood.py`): Live Pipeline, Source
  Contracts, Engineering Stack, Data Quality, Architecture Decisions, Administration, Wiki.
- Note: `STRESS_LAB_ENABLED=False` and `SIDEBAR_ENABLED=False`; the old `pages/3_Stress_Lab.py` is disabled but present.

**Target IA, three surfaces, two of them MIRRORED engineering pillars:**

1. **Business surface** (retained, upgraded): the banking/exec audience view. Predictive Analytics becomes REAL
   (per-bank distress score + SHAP reason codes), and a real **Scenario / Stress Lab** replaces the decommissioned
   fabricated one (insert test bank, hold out a bank, hypothetical what-if).
2. **Data Engineering surface** = today's Technical surface, rebadged "Data Engineering" with its existing sections.
3. **AI surface** = NEW, mirroring the DE surface's section flow 1:1 so the two engineering pillars read as parallel
   disciplines. (Naming per Surya: the three surfaces are Business / Data Engineering / AI.)

This is a **complete IA overhaul**, not a UI tweak: a shared three-way top navigation (Business / Data Engineering /
AI), a unified page shell used by all surfaces, and the fixed mini-wiki. The Business surface stays standard; the two
engineering surfaces are structurally mirrored.

DE-surface section → AI-surface mirror (same flow, same UX shell):

| Data Engineering section (existing) | AI surface mirror (new) |
|---|---|
| Live Pipeline (run status) | AI Pipeline (train/score DAG runs, champion alias, last run) |
| Source Contracts (data contracts) | Feature Contracts (feature defs, PIT rules, input schema) |
| Engineering Stack | AI Stack (MLflow, LightGBM, FastAPI, Evidently, skops, DuckDB) |
| Data Quality | Model Quality (PR-AUC/recall@k/Brier/calibration, by-cohort, by-segment, drift) |
| Architecture Decisions (ADRs) | Model Decisions (hazard framing, monotonic, calibration, SR 11-7) |
| Administration | Model Administration (registry aliases, champion/challenger, retrain triggers) |
| Wiki | AI Wiki (hazard, calibration, SHAP, drift), same fixed mini-wiki UX |

The top navigation switches between Business / Data Engineering / AI. Every section in both engineering surfaces
exposes the underlying real artifact (SQL, feature defs, run metrics, SHAP, registry state) so **no layer is
invisible**, maximum visibility is a hard final-QA criterion. The Wiki UX is fixed (no full reload per click) and
shared by all three surfaces.

## 0. Goal

Add a production-grade, regulator-defensible **bank financial-distress early-warning model** to FinLens, surfaced
in the Streamlit app, served by FastAPI, tracked in MLflow, monitored by Evidently, and orchestrated by Airflow , 
running robustly alongside the existing DuckDB + Postgres + dbt stack. It must support: train/test by time,
held-out banks, "insert a test bank", and hypothetical-scenario scoring.

## 1. The data problem (resolved)

The existing `ingestion/qbp.py` aggregates all banks into ONE row per quarter (system totals). That cannot support a
per-bank model. **Resolution:** add a new institution-level source.

- **FDIC BankFind Suite financials API** `https://api.fdic.gov/banks/financials`, public, no key. Per-CERT quarterly
  rows. Verified: 8,024 institutions for 2010Q1 with `CERT, REPDTE, ASSET, NETINC, ROA, EQ, P9LNLS (noncurrent),
  DRLNLS (charge-offs), DEP`, plus many more fields available.
- **FDIC institutions API** `https://api.fdic.gov/banks/institutions`, `CERT, NAME, STALP, ACTIVE, ESTYMD, ENDEFYMD,
  charter/class` for entity metadata + size/region/charter segments.
- **FDIC failed banks** (already ingested) → failure labels by `CERT` + `closing_date`. **Staging extension required:**
  `stg_fdic_failed_banks.sql` currently projects only 9 columns; it must additionally expose closing date +
  **resolution/transaction type** (e.g., `CLOSCD`/`RESTYPE`/`FAILDATE` from the source CSV) so the labeler can
  distinguish true failures from assisted/healthy resolutions (censoring).
- **FRED macro** (already ingested) → macro context features. **Commit to ALFRED as-released (vintage) values from v1**
  (free, no key) to eliminate the macro look-ahead leak rather than carrying it as a caveat.

Training window: **2008Q1 → present** (captures the 2008-2012 wave of ~450+ failures + 2023 SVB/Signature/First
Republic). Optional later extension to 1992+ for additional crisis coverage. The existing aggregate QBP path stays as
the system-level "Stress Pulse" view; the new institution panel powers the ML.

## 2. Problem framing (the modeling decision)

- **Unit of analysis:** bank-quarter (one row per CERT per REPDTE) → a **discrete-time hazard panel**.
- **Target:** binary `fails_within_H` = institution's CERT appears in the FDIC failed-banks list with
  `closing_date` within H quarters after the observation quarter. Primary horizon **H = 4**; secondary **H = 8**.
- **Why hazard, not next-quarter logit:** discrete-time hazard on a bank-quarter panel uses time-varying covariates
  and the full panel, beats single-period logit (BIS two-step; literature consensus), and reduces to binary
  classification a GBM can fit directly.
- **Rare-event handling:** long training window spanning crises; `scale_pos_weight`/class weights inside the GBM
  (NOT SMOTE across the time boundary); recalibrate after weighting. Failure is rare but H=4/8 over 2008-2012 yields
  a workable positive count.
- **Censoring:** banks that exit via healthy merger/acquisition are right-censored, NOT labeled failures (uses FDIC
  `ENDEFYMD` + failed-banks list to distinguish). Mislabeling acquisitions as failures is a known silent leak.
- **Scope note:** the public-data target is *failure* (FDIC RESTYPE), not the examiner
  "problem bank" flag; that is the label this project models. (System-level problem-bank counts
  are used only in aggregate for context.)

## 3. Features (CAMELS-aligned, all from public fields)

Derived per bank-quarter, then enriched:
- **Capital:** EQ/ASSET (equity ratio); Tier-1/leverage where available.
- **Asset quality:** noncurrent_rate = P9LNLS/loans; nco_rate = DRLNLS/loans; provisioning.
- **Management/Growth:** efficiency ratio; YoY asset growth (abnormal growth is a classic precursor).
- **Earnings:** ROA, ROE, NIM, net income margin.
- **Liquidity:** loans/deposits, funding cost, brokered/wholesale share where available.
- **Sensitivity (the SVB lesson):** (AFS+HTM unrealized losses)/Tier-1 where fields exist, highest-value 2023-regime
  signal. **Coverage caveat:** these fields are sparse/uneven in public Call Report data pre-2020; treat as a
  post-2020 enhancement feature with explicit null-handling, and do NOT oversell the 2023-regime claim for earlier
  cohorts. Gracefully degrade (missing-indicator) where unavailable.
- **Engineering:** levels + QoQ/YoY deltas (rate-of-deterioration) + **peer z-scores** within asset-size band and
  region.
- **Macro joins (FRED):** term spread (DGS10-DGS2), BAA10Y credit spread, NFCI, UNRATE, CPI; selected interactions
  (e.g., unrealized-loss × rate level).

**Point-in-time discipline (make-or-break):**
- Call Reports file ~30 days after quarter-end → features for scoring date must lag by ≥1 filing cycle (reporting-lag
  embargo).
- Label window strictly in the future relative to features.
- Macro: use as-released vintage (ALFRED) from v1 (free, no key), no latest-vintage fallback, eliminating the macro
  look-ahead leak by construction.
- Group by `CERT` so the same bank never straddles train/test for an event window.

## 4. Model

- **Primary:** LightGBM gradient-boosted classifier (XGBoost interchangeable) on the bank-quarter panel, with
  **monotonic constraints** (more capital → lower risk; higher noncurrent/NCO/unrealized-loss → higher risk) for
  regulatory defensibility and to prevent perverse relationships.
- **Benchmark (mandatory):** penalized logistic regression (the regulatory reference, SCOR/SEER lineage). The GBM
  must beat it to justify nonlinearity.
- **Imbalance:** `scale_pos_weight` / class weights; optional in-fold resampling only, never across the time split.
- **Calibration:** `CalibratedClassifierCV(FrozenEstimator(model), method=...)` on a separate temporal holdout;
  isotonic if enough positives else sigmoid/Platt; decision by reliability curve + Brier. Serve the **calibrated**
  probability.
- **Explainability:** SHAP TreeExplainer (global ranking + per-bank local reason codes).

## 5. Validation

- **Scheme:** rolling-origin / expanding-window **out-of-time** by quarter, with reporting-lag **embargo** between
  train and test, grouped by CERT.
- **Metrics:** PR-AUC / Average Precision (primary); recall@k & precision@k at a supervisory review budget; Brier +
  reliability curve; ROC-AUC reported for comparability only; **accuracy is never the headline**.
- **By-cohort reporting:** crisis vs calm years separately (a model that only works in 2009-2010 is not production
  ready). **Pre-stated expectation:** in calm cohorts (e.g., 2015-2022, near-zero failures) PR-AUC may be very low or
  undefined simply because positives are absent, this is expected, not a broken model, and is reported honestly
  rather than hidden.
- **Realistic bar (anti-fantasy):** out-of-time ROC-AUC ≈ 0.92-0.97 at 1y horizon is credible; >0.98 OOT → suspect
  leakage. PR-AUC much lower than ROC-AUC (0.2-0.6 typical) and that is normal. No fabricated metrics, every number
  comes from a real run logged to MLflow.

## 6. MLOps stack (2026-current, local-first)

- **Tracking/registry:** MLflow 3.3+ with **Postgres backend** + local artifact volume. **Aliases + tags** (champion/
  challenger), NOT deprecated stages. Every run stamped with git SHA + data snapshot id.
- **Serialization:** native LightGBM/XGBoost booster (`.txt`/`.json`) + **skops.io** for the sklearn pipeline
  (preprocessing + calibrator). **No raw pickle across a trust boundary.**
- **Serving:** plain **FastAPI** (extend existing `api/`), model loaded once via lifespan into app state, **Pydantic
  v2** request/response with range validation, `/predict` (single) + `/predict/batch` (vectorized), returns calibrated
  prob + model version/alias + SHAP top drivers + decision flag. `OMP_NUM_THREADS=1` in the container; fixed worker
  count; `/health` + `/ready` (ready fails if model not loaded). Last-known-good artifact cached locally for registry-
  outage resilience.
- **Data/features:** point-in-time **DuckDB snapshots** (partition by as_of_date, immutable). **No Feast** (overkill at
  this scale). Seeds + pinned deps + pinned base image digest.
- **Monitoring:** **Evidently 0.7.x** (`Report`/`Dataset`/`DataDefinition` API, not deprecated `ColumnMapping`/
  `Dashboard`). Data drift (PSI/Wasserstein), **prediction drift** (earliest signal), feature freshness/null-rate;
  scheduled report + alert; drift- or schedule-triggered retrain.
- **CI/CD:** GitHub Actions, code tests (incl. serving: schema-reject, batch==single, health); data-validation gate;
  **model metric gate** (PR-AUC/recall@k/Brier thresholds + champion-vs-challenger regression gate + calibration
  gate); manual promotion to champion alias.

## 6.1 Resource budget (against the REAL VPS allocation: $0, bounded memory)

Existing `docker-compose.prod.yml` hard caps already commit ~6 GB: web/public/api/finlens-db 512m×4, airflow-web 2g,
scheduler 1.5g, airflow-db 512m. The ML subsystem must add minimal RESIDENT memory and zero billable activity.

- **MLflow:** reuse the **existing Postgres** (`finlens-db`) as the tracking backend (separate schema), artifact store
  = **local Docker volume only**. MLflow server container `mem_limit: 512m`. Net new resident memory ≈ 512m.
- **Training:** runs as a **one-shot Airflow task inside the existing scheduler** (1.5g cap), NOT a resident service.
  Panel size ≈ 5-8k CERTs × ~70 quarters ≈ 300-500k rows × dozens of features fits well under 1.5g (LightGBM is
  histogram-based and memory-frugal). `OMP_NUM_THREADS=1`, capped `n_jobs`.
- **SHAP:** TreeExplainer run on a **sampled background set (≤2,000 rows)** and capped explained rows so peak RSS stays
  bounded; full-dataset SHAP is forbidden.
- **Serving:** model is tens of MB; loaded once at startup; fits inside the existing api container budget or a small
  dedicated `ml-api` container at `mem_limit: 512m`.
- **$0 enforcement (by construction, not by promise):** no S3 PUT, no Snowflake, no paid API, enforced structurally:
  1. **Dedicated ML settings** `ml/finlens_ml/config.py` exposes only ML fields (paths, horizons, thresholds, MLflow
     URI, DuckDB path). It does **not** expose AWS credentials, buckets, or `aws_s3_mirror_enabled`. ML code cannot
     reach an S3 config because it isn't in its settings object.
  2. **Import guard in CI:** an import-linter contract (or an AST test) that **fails the build** if anything under
     `ml/finlens_ml/` imports `finlens.aws`, `boto3`, or `snowflake`. This makes the no-PUT property hold by
     construction; a future commit that adds a billable call cannot merge.
  3. All sources (FDIC, FRED/ALFRED) are free/no-key. The guard + dedicated settings together turn "$0" from author
     discipline into a CI-enforced invariant.

Net new resident footprint: ~512m (MLflow) + optional ~512m (ml-api) ≈ ≤1 GB, within headroom; training is transient.

## 7. Governance (SR-aligned)

- **SR 11-7** (Fed/OCC, 2011), the established model-risk management guidance and the
  reference this project aligns to. Principles-based; this is a portfolio demonstration, so we
  claim **"aligned with SR 11-7 principles"**, never "compliant"/"a rule".
- **SR 11-7 three pillars** (the substance): conceptual soundness, ongoing monitoring, outcomes analysis;
  effective challenge; documentation + model inventory.
- **Explainability:** SHAP + monotonic constraints; reason codes framed as validator/supervisor-facing (NOT ECOA/Reg B
  adverse-action, no consumer applicant exists; claiming otherwise is misapplication).
- **Fairness, anti-theater:** an institution-level model has **no protected class**. We do **cross-segment performance
  equity** (recall/precision/calibration across asset-size tiers, regions, charter types) as a *model-soundness*
  check (SR 11-7 outcomes analysis), using Fairlearn `MetricFrame` purely as a slicing convenience, and we state
  explicitly that demographic-parity/disparate-impact/four-fifths do NOT apply. No fake fair-lending claims.
- **Artifacts:** model card, validation report, data lineage, monitoring plan, model-inventory entry.

## 8. Repo layout (new)

```
ml/
  finlens_ml/
    __init__.py
    config.py            # ML settings (paths, horizons, thresholds, MLflow URI, DuckDB), NO AWS fields
    data.py              # build bank-quarter panel from DuckDB
    labels.py            # failure labeling + censoring + horizon windows
    features.py          # CAMELS ratios, deltas, peer z-scores, macro joins, PIT
    splits.py            # rolling-origin OOT splits + embargo + group-by-cert
    train.py             # LightGBM + logit benchmark + calibration → MLflow
    evaluate.py          # PR-AUC/recall@k/Brier/calibration/by-cohort/by-segment
    explain.py           # SHAP global + local reason codes
    calibrate.py         # FrozenEstimator + isotonic/Platt
    registry.py          # MLflow alias/tag helpers
    predict.py           # load champion, score single/batch/hypothetical
    monitor.py           # Evidently drift + prediction drift reports
    model_card.py        # generate model card + validation report
ingestion/fdic_institutions.py   # new per-CERT financials + institutions ingest
dbt/models/.../ (institution staging → intermediate panel → mart)
airflow/dags/dag_ml_train_score.py
api/routers/predict.py            # FastAPI inference + explanation endpoints
streamlit_app/pages/3_Predictive_Analytics.py  # replace "coming soon" with real interactive tab
docs/ml/  (architecture, model card, validation report, governance)
ml/tests/                         # unit + model + serving tests
docker-compose additions: mlflow service (local)
```

**Decommission (remove fabricated assets, Constraint 4):**
- Delete `src/finlens/stress_lab.py` (hardcoded "Washington Mutual Bank" demo records, random `train_test_split`/
  `StratifiedKFold`, accuracy/ROC-AUC headline, fabricated and leakage-prone).
- Delete `streamlit_app/pages/3_Stress_Lab.py` and `tests/streamlit/test_stress_lab.py`; remove `STRESS_LAB_ENABLED`
  references in `page_shell.py`.
- Reconcile the duplicate `pages/3_*` numbering: the new real Scenario/Stress Lab lives in the Business surface as a
  properly-numbered page (no two `pages/3_*` files). The hardcoded demo dataset is **removed, not migrated**, the new
  lab scores against the real trained model only.
- Refactor `api/main.py` from module-level model init to a FastAPI **lifespan** loader (current code uses module-level
  init; the new serving path must not copy that pattern).

## 9. Execution phases (each gated by adversarial reviewer; no advance without sign-off)

1. **P0 Architecture** (this doc) → architect reviewer, 100% required.
2. **P1 Data foundation:** institution ingestion + dbt panel + labels → ML reviewer.
3. **P2 Features + splits:** feature pipeline + PIT + OOT splits, leakage tests → ML reviewer.
4. **P3 Model + calibration + eval:** train, benchmark, calibrate, real metrics to MLflow → ML reviewer.
5. **P4 Explain + governance:** SHAP, model card, validation report, segment equity → ML reviewer.
6. **P5 Serving + monitoring:** FastAPI endpoints, Evidently, CI gates → ML reviewer.
7. **P6 UI:** two-pillar restructure (DE layer + mirrored ML layer), interactive scenario tab (test bank / hold-out /
   hypothetical), full per-layer visibility, Wikipedia mini-wiki fix (no full reload), content enrichment → reviewer.
8. **P7 Final QA + local deploy:** end-to-end run, teardown QA, reject anything fake/unstable → same reviewer.

Commit to remote `machine-learning-portfolio` at the end of each phase.

## 10. Local-first robustness

- Everything runs via docker-compose locally (mlflow + api + existing services) OR via local Python venv against the
  local DuckDB, mirroring the VPS topology so the eventual VPS deploy is a config swap, not a rewrite.
- Memory bounds + `OMP_NUM_THREADS=1` honored locally so behavior matches the constrained VPS.
- No fabricated data, no fabricated metrics, reproducible (seeds + pins).
