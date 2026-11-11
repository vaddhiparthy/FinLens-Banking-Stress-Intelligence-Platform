# Pooled evaluation mismeasures rare-event bank-failure prediction: a failure-cause decomposition

*FullLens working paper / preprint draft (S4). Assembled from the committed component analyses;
every number is reproducible from the artifacts and scripts cited inline. This is a portfolio
research artifact, not peer-reviewed.*

## Abstract

Bank failure is highly predictable from public accounting data, a result established at scale
by Correia, Luck & Verner (2025). We do not contest it. We show that the standard *evaluation*
of such predictors is biased in a specific, correctable way: pooled rare-event metrics are
computed over a positive set that mixes financially-observable failures with failures (notably
fraud) that leave no accounting signature and are structurally unrankable by any
accounting-based model. Using the 2019-2026 U.S. out-of-time failures (66 events) with failure
causes sourced from primary regulator documents (FDIC OIG, OCC, Federal Reserve, Treasury OIG),
we decompose the positive set by failure visibility and report performance on the
financially-addressable subset alongside the pooled figure. The pooled-to-addressable lift is
positive across five model families (penalized logistic regression, random forest, XGBoost,
constrained and unconstrained gradient boosting), so the gap is a property of the evaluation,
not of any model. The result is stable to the label source (author thresholds vs regulator
cause agree on 92% of positives) and to a 2020 reporting-regime feature break. We are not aware
of prior work that conditions failure-prediction evaluation on failure cause or reports an
addressable-versus-pooled metric. Full framing: [ABSTRACT.md](ABSTRACT.md).

## 1. Introduction

The motivating problem is that the field competes on aggregate scores (accuracy, ROC-AUC,
PR-AUC) against a single binary failure label. At a sub-1% base rate, accuracy is uninformative
(a published model reports 98.4% accuracy; Hu et al. 2025), and even PR-AUC, the right rare-event
metric, is biased when the positive set contains events no accounting model can rank. We make
that bias explicit and correct it.

## 2. Related work

Established predictability (Correia, Luck & Verner 2025, ROC-AUC ~80-85%, pooled label); the
near-twin pipeline (Shakiba CMC thesis 2026, ROC-AUC > 0.97, which drops RWA ratios for the
post-2020 CBLR break that we show is harmful to drop); ML papers (Hu/Shao/Zhang FRL 2025;
Vallarino JEA 2024); the field survey (Citterio et al. SEPS 2024, no cause-conditional
dimension); and the classic lineage (Cole & Gunther 1998/1995). Full positioning and the
novelty check: [RELATED_WORK.md](RELATED_WORK.md).

## 3. Data

A per-bank-quarter panel from FDIC/FFIEC public Call Reports, 448,661 bank-quarters across
~8,800 banks, 2008Q1-2026Q1, with 34 CAMELS-aligned ratios. The label is failure within four
quarters (FDIC RESTYPE=FAILURE), with merger/acquisition exits right-censored. The out-of-time
holdout is the last 28 quarters with a reporting-lag embargo; it contains 66 real failures
across 19 distinct banks. The gold mart `bank_quarterly_risk_facts` (dbt) materializes the
bank-quarter risk facts; a Great Expectations suite gates schema, freshness, and null-rate.

## 4. Methods

- **Served model (vehicle, not contribution).** Calibrated, monotone-constrained gradient-
  boosted discrete-time hazard model; out-of-time PR-AUC 0.301, ROC-AUC 0.855, recall@200 0.545.
  A GRU sequence challenger and RF/XGBoost baselines were tested and do not beat it
  ([SEQUENCE_CHALLENGER.md](SEQUENCE_CHALLENGER.md)).
- **External failure-cause labels (C1).** `ml/finlens_ml/failure_cause_labels.py`: the primary
  cause for all 19 OOT failed banks from regulator sources (18/19 primary-regulator), mapped
  credit -> visible, rate/liquidity -> visible, fraud -> invisible.
- **Decomposition (C2) and addressable PR-AUC.** [FAILURE_DECOMPOSITION.md](FAILURE_DECOMPOSITION.md).
- **Cross-model pooled-vs-addressable (C3).** `ml/scripts/pooled_vs_addressable.py`.
- **CBLR feature-break robustness (C4).** `ml/scripts/cblr_robustness.py`.
- **Label-source sensitivity (C5).** Threshold vs regulator-cause labels.
- **Competing risks (S3).** Merger-censoring bias bound + discrete-time Fine-Gray, positioned
  vs the methods literature ([COMPETING_RISKS.md](COMPETING_RISKS.md)).

## 5. Results

- Addressable PR-AUC **0.382 [0.250, 0.530]** vs pooled **0.301 [0.191, 0.438]** (same percentile
  bootstrap; intervals overlap heavily, so this is a structural reattribution, not a separable
  gain). The number depends only on the invisible/visible boundary, confirmed by a 52-positive
  credit<->rate/liquidity swap test that leaves it unchanged.
- **Cross-model lift (the core claim):** pooled -> addressable is positive for every family,
  monotone GBM +0.081, RF +0.079, XGBoost +0.073, unconstrained GBM +0.072, logit +0.041. The
  gap is a property of the evaluation set, not the model.
- **Label-source stability (C5):** addressable PR-AUC 0.382 (thresholds) vs 0.389 (regulator
  cause), 92% agreement on positives; the only disagreements (Lindsay, Ericson) are fraud-caused
  but financially visible.
- **CBLR robustness (C4):** native-null and explicit indicator give identical addressable PR-AUC;
  dropping the feature (a prior-work choice) craters it.
- **Mechanism:** the by-filing-year collapse is two distinct causes, the 2022 filing cohort is
  the 2023 rate/liquidity wave a credit model under-weights; the 2024 cohort is fraud failures
  with no signal. The "invisible" class is exactly the named fraud failures (Enloe, Heartland,
  Lindsay, Pulaski, Santa Anna), verifiable against the FDIC OIG record.

## 6. Limitations

The binding limit is statistical power: 66 out-of-time failures give the paired test ~6% power,
so no single number is individually separable; every figure is reported with intervals and the
claim is the consistent *direction* across models and label sources. This is a data-existence
wall (failures that did not happen cannot be created), not incomplete work. Pre-2001 Call
Reports do not exist in machine-readable form. Scope is public FDIC/FFIEC data.

## 7. Reproducibility

Branch `machine-learning-portfolio`. Served model frozen at commit `7473608`. Each result has a
committed script + artifact: `failure_cause_labels.py`, `failure_decomposition.py` +
`failure_decomposition.json`, `pooled_vs_addressable.py` + `.json`, `cblr_robustness.py` + `.json`,
`sequence_challenger.py`/`sequence_sweep.py` + `.json`, `fine_gray.py`/`competing_risks.py`. Tests in
`ml/tests/test_failure_decomposition.py`. $0, open-source, local-first (DuckDB, Chroma, Ollama).

## 8. The accompanying system (capstones)

The analysis sits on a $0 end-to-end platform: a Data Engineering layer (FDIC/FRED ingestion,
Airflow DAGs, dbt medallion + the `bank_quarterly_risk_facts` gold mart, Great Expectations
gate), an ML serving layer (MLflow registry, FastAPI `/predict-failure-risk` with SHAP,
Evidently drift), and a RAG Analyst Assistant (local Chroma index of the regulator failure
corpus, LangGraph retrieve -> live-model-grounding -> cited synthesis via local Ollama, RAGAS-style
20-Q eval with hit@4 1.0 and citation-grounding 1.0, local observability, a Streamlit page). See
[PROJECT_CAPSTONES.md](../PROJECT_CAPSTONES.md).

## References

Correia, Luck & Verner (2025) "Failing Banks" (NY Fed SR 1117 / NBER w32907 / arXiv 2506.06082).
Shakiba (2026) CMC Senior Thesis. Hu, Shao & Zhang (2025) Finance Research Letters 75. Vallarino
(2024) J. Economic Analysis 3(1). Citterio et al. (2024) Socio-Economic Planning Sciences 92.
Cole & Gunther (1998) JFSR 13(2); (1995) JBF 19(6). Fine & Gray (1999) JASA 94. Austin, Lee &
Fine (2016) Circulation 133. Berger et al. (2020) Biostatistics 21(3). Schmid & Berger (2021)
WIREs Computational Statistics 13(5).
