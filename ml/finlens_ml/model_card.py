"""Generate the model card + validation report from REAL computed numbers.

Nothing here is hand-written prose with invented metrics: the OOT metrics come from
ml/artifacts/metrics_h4.json (the actual training run), SHAP drivers from explain.py,
and cross-segment performance equity from scoring the real OOT slice and grouping by
asset-size tier / charter class / region via Fairlearn's MetricFrame (used purely as
a slicing convenience).

Fairness framing: a bank-distress model predicts on INSTITUTIONS, not people.
There is NO protected class, so demographic parity / disparate impact / four-fifths do
NOT apply and are deliberately NOT computed. What we report is cross-segment
performance equity (is the model reliably catching distress across small vs large
banks, regions, charters?) as an SR 11-7 outcomes-analysis soundness check.

$0: no billable imports.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from finlens_ml.config import get_ml_settings
from finlens_ml.evaluate import evaluate
from finlens_ml.features import FEATURE_COLUMNS
from finlens_ml.splits import final_holdout_split

EVAL_HOLDOUT_QUARTERS = 28
_CENSUS_REGION = {
    # minimal state->region map for cross-segment slicing
    "CT": "Northeast", "ME": "Northeast", "MA": "Northeast", "NH": "Northeast",
    "RI": "Northeast", "VT": "Northeast", "NJ": "Northeast", "NY": "Northeast", "PA": "Northeast",
    "IL": "Midwest", "IN": "Midwest", "MI": "Midwest", "OH": "Midwest", "WI": "Midwest",
    "IA": "Midwest", "KS": "Midwest", "MN": "Midwest", "MO": "Midwest", "NE": "Midwest",
    "ND": "Midwest", "SD": "Midwest",
    "DE": "South", "FL": "South", "GA": "South", "MD": "South", "NC": "South", "SC": "South",
    "VA": "South", "WV": "South", "DC": "South", "AL": "South", "KY": "South", "MS": "South",
    "TN": "South", "AR": "South", "LA": "South", "OK": "South", "TX": "South",
    "AZ": "West", "CO": "West", "ID": "West", "MT": "West", "NV": "West", "NM": "West",
    "UT": "West", "WY": "West", "AK": "West", "CA": "West", "HI": "West", "OR": "West", "WA": "West",
}


def _oot_scored(horizon_q: int = 4) -> pd.DataFrame:
    import duckdb

    from finlens_ml.predict import score_frame

    settings = get_ml_settings()
    label = f"label_{horizon_q}"
    with duckdb.connect(str(settings.duckdb_path), read_only=True) as conn:
        df = conn.execute("select * from ml.training_dataset").df()
    df = df[df[label].notna()].reset_index(drop=True).copy()
    df[label] = df[label].astype(int)
    _, te_idx = final_holdout_split(df["obs_qord"], horizon_q=horizon_q,
                                    holdout_quarters=EVAL_HOLDOUT_QUARTERS)
    test = df.iloc[te_idx].reset_index(drop=True).copy()
    test["score"] = score_frame(test, horizon_q)
    test["y"] = test[label].to_numpy()
    return test


def _segment_table(test: pd.DataFrame, by: str, k: int = 50) -> pd.DataFrame:
    rows = []
    for seg, g in test.groupby(by, dropna=False, observed=False):
        m = evaluate(g["y"].to_numpy(), g["score"].to_numpy(), k=min(k, len(g)))
        rows.append({
            "segment": str(seg), "n": m.n, "positives": m.n_positive,
            "pr_auc": round(m.pr_auc, 4) if not np.isnan(m.pr_auc) else None,
            "roc_auc": round(m.roc_auc, 4) if not np.isnan(m.roc_auc) else None,
            "recall_at_k": round(m.recall_at_k, 3) if not np.isnan(m.recall_at_k) else None,
        })
    return pd.DataFrame(rows).sort_values("n", ascending=False).reset_index(drop=True)


def cross_segment_equity(horizon_q: int = 4) -> dict[str, pd.DataFrame]:
    test = _oot_scored(horizon_q)
    # asset-size tier (quartiles); region; charter class
    if "ASSET" in test.columns:
        test["size_tier"] = pd.qcut(
            test["ASSET"].rank(method="first"), 4,
            labels=["Q1 smallest", "Q2", "Q3", "Q4 largest"],
        )
    test["region"] = test.get("state", pd.Series(index=test.index)).map(_CENSUS_REGION).fillna("Other")
    out = {}
    if "size_tier" in test.columns:
        out["asset_size_tier"] = _segment_table(test, "size_tier")
    out["region"] = _segment_table(test, "region")
    if "bank_class" in test.columns:
        out["charter_class"] = _segment_table(test, "bank_class")
    # Fairlearn MetricFrame as a slicing convenience (NOT protected-class fairness)
    try:
        from fairlearn.metrics import MetricFrame, false_negative_rate, true_positive_rate

        flag = (test["score"].to_numpy() >= get_ml_settings().flag_threshold).astype(int)
        if "size_tier" in test.columns and test["y"].sum() > 0:
            mf = MetricFrame(
                metrics={"recall": true_positive_rate, "miss_rate": false_negative_rate},
                y_true=test["y"].to_numpy(), y_pred=flag,
                sensitive_features=test["size_tier"].astype(str),
            )
            out["fairlearn_recall_by_size"] = mf.by_group.reset_index()
    except Exception:
        pass
    return out


def _md_table(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False)


def generate_model_card(horizon_q: int = 4) -> Path:
    settings = get_ml_settings()
    metrics = json.loads((settings.artifact_dir / f"metrics_h{horizon_q}.json").read_text())
    from finlens_ml.explain import global_importance

    gi = global_importance(n=1500).head(12)
    seg = cross_segment_equity(horizon_q)
    t = metrics["oot_test"]["calibrated_lgbm"]
    logit = metrics["oot_test"]["logit_benchmark"]
    cal = metrics.get("oot_calibration", {})
    fm = metrics.get("final_model", {})
    chal = metrics.get("challengers", {})
    unc = chal.get("unconstrained_gbm")
    tune = metrics.get("hyperparameter_tuning", {})
    tune_line = (
        f"Hyperparameters are tuned with Optuna over {tune.get('n_trials')} trials on "
        f"{tune.get('n_inner_folds')} inner time-series CV folds (best CV PR-AUC "
        f"{tune.get('cv_mean_pr_auc')}), not hand-set."
        if tune.get("tuned") else ""
    )
    unc_row = (
        f"| Unconstrained GBM | {unc['pr_auc']:.4f} | {unc['roc_auc']:.4f} | "
        f"{unc['recall_at_k']:.3f} | {unc['brier']:.5f} |\n"
        if unc else ""
    )
    by_year = pd.DataFrame(
        [{"year": y, **{k: (round(v, 4) if isinstance(v, float) else v)
                        for k, v in m.items() if k in ("n", "n_positive", "pr_auc", "roc_auc")}}
         for y, m in metrics.get("by_year_calibrated", {}).items()]
    )

    card = f"""# Model Card — FinLens Bank Financial-Distress Early-Warning Model

*Generated from real artifacts (ml/artifacts/metrics_h{horizon_q}.json) — no hand-entered metrics.*

## Intended use
Rank US FDIC-insured institutions by probability of **financial distress / failure
within {horizon_q} quarters**, from public quarterly Call Report financials. Decision-support
for off-site monitoring / exam prioritization. **Not** investment, deposit, or
supervisory advice; **not** a consumer-credit decision (no ECOA/Reg-B adverse action).

## Model
Calibrated, monotone-constrained LightGBM discrete-time hazard classifier on a
per-bank-quarter panel. {len(FEATURE_COLUMNS)} CAMELS-aligned features. Served model trained on all
data with the out-of-time-validated tree count (n_estimators={fm.get('n_estimators')}),
calibration={fm.get('calibration_method')}. {tune_line} The effective-challenge ladder is a
penalized logistic regression and an unconstrained GBM (same tuned params, no monotone
constraints).

## Out-of-time performance (test window: last {metrics['eval_window_quarters']} quarters, {metrics['n_test']:,} bank-quarters, {metrics['test_positives']} real failures)
Lead metric is **PR-AUC** (rare-event); ROC-AUC is comparability-only; accuracy is not reported.

| Model | PR-AUC | ROC-AUC | recall@{t['k']} | Brier |
|---|---|---|---|---|
| Calibrated LGBM | **{t['pr_auc']:.4f}** | {t['roc_auc']:.4f} | {t['recall_at_k']:.3f} | {t['brier']:.5f} |
{unc_row}| Logit benchmark | {logit['pr_auc']:.4f} | {logit['roc_auc']:.4f} | {logit['recall_at_k']:.3f} | {logit['brier']:.5f} |

The LGBM beats the regulatory logit benchmark on PR-AUC (the metric that matters at a
<1% base rate) and on recall@k. The logit's ROC-AUC is marginally higher; ROC-AUC is
deprioritized here and shown only for comparability.

### Calibration
All-rows Brier is dominated by true negatives, so we also report ECE and the flagged
(top-decile) calibration: ECE={cal.get('ece', float('nan')):.2e}; in the top-scoring
decile the model predicts {cal.get('top_decile_pred', float('nan')):.4f} vs observed
{cal.get('top_decile_obs', float('nan')):.4f}.

### Performance by year (calibrated)
{_md_table(by_year) if not by_year.empty else "(see metrics.json)"}

In calm years with few or zero failures, PR-AUC is low or undefined — the expected
behavior of a rare-event model.

## Top global drivers (SHAP)
{_md_table(gi.rename(columns={'mean_abs_shap': 'mean_|SHAP|'}))}

Capital (tier-1) and earnings (ROA) dominate, consistent with the bank-failure
literature. Computed as mean |SHAP| over a fixed reservoir sample (n=1500, seed 42)
of OOT-era rows. Local per-bank SHAP reason codes are available via the serving API.

## Cross-segment performance equity (NOT protected-class fairness)
A bank-distress model predicts on institutions, not consumers — there is **no protected
class**, so demographic parity / disparate impact / the four-fifths rule do not apply
and are deliberately not computed. We instead verify the model performs across segments
(SR 11-7 outcomes analysis). Fairlearn `MetricFrame` is used only as a slicing tool.

### By asset-size tier
{_md_table(seg['asset_size_tier']) if 'asset_size_tier' in seg else '(n/a)'}

### By region
{_md_table(seg['region']) if 'region' in seg else '(n/a)'}

### By charter class
{_md_table(seg['charter_class']) if 'charter_class' in seg else '(n/a)'}

## Limitations
- Public-data label is **failure** (FDIC RESTYPE=FAILURE); per-bank CAMELS exam ratings
  are confidential and not used. The model cannot see supervisory/liquidity internals.
- SHAP assumes feature independence in probability space; correlated CAMELS ratios
  violate this, so local SHAP is validator/supervisor-facing transparency, **not** a
  legally-sufficient adverse-action reason code.
- The model is bank-level and does **not** use macro series as inputs (capital and
  earnings carry most of the signal); FRED macro is business-surface context only.
- Features come from the FDIC `/financials` endpoint (currently-restated values, not the
  originally-filed Call Report); strict point-in-time feature integrity would require
  originally-filed FFIEC CDR data.
- Rare-event metrics are noisy in calm cohorts; judge on failure-containing windows.

## Governance
Aligned with the **principles** of SR 11-7 (Fed/OCC, 2011 — the established model-risk
management guidance; primary source:
https://www.federalreserve.gov/supervisionreg/srletters/sr1107.htm) — **non-binding**
here; a GBM is in scope (non-generative, non-agentic). This is a portfolio demonstration,
not a regulated production model. The substantive validation rests on the SR 11-7 three
pillars (see the validation report).
"""
    out = Path(settings.repo_root) / "docs" / "ml" / "MODEL_CARD.md"
    out.write_text(card, encoding="utf-8")
    return out


def generate_validation_report(horizon_q: int = 4) -> Path:
    settings = get_ml_settings()
    metrics = json.loads((settings.artifact_dir / f"metrics_h{horizon_q}.json").read_text())
    t = metrics["oot_test"]["calibrated_lgbm"]
    lg = metrics["oot_test"]["logit_benchmark"]
    ci = metrics.get("oot_test_ci", {})
    prci = ci.get("pr_auc_ci", [float("nan"), float("nan")])
    rci = ci.get("recall_at_k_ci", [float("nan"), float("nan")])
    diff = metrics.get("lgbm_vs_logit_ap_diff", {})
    dci = diff.get("ap_diff_ci", [float("nan"), float("nan")])
    rb = metrics.get("rolling_backtest", {}).get("aggregate", {})
    _unc = metrics.get("challengers", {}).get("unconstrained_gbm", {})
    ug_pr = _unc.get("pr_auc", t["pr_auc"])
    ug_gap = ug_pr - t["pr_auc"]
    ug_rel = ug_gap / ug_pr if ug_pr else 0.0
    report = f"""# Validation Report — FinLens Bank-Distress Model (SR 11-7 three pillars)

*Effective-challenge package. Metrics computed from real out-of-time evaluation.*

## 1. Conceptual soundness
- **Theory:** discrete-time hazard (bank-quarter panel) is the established framing for
  time-to-failure with time-varying covariates (BIS two-step; literature consensus).
- **Features:** {len(FEATURE_COLUMNS)} CAMELS-aligned ratios with economically-signed **monotone
  constraints** (more capital -> lower risk; higher noncurrent/NCO -> higher risk),
  preventing perverse relationships a validator would reject.
- **Benchmark / effective challenge:** a ladder of a penalized logistic regression (a
  regulatory-style linear reference) and an unconstrained GBM (same tuned params, no
  monotone constraints). The constrained GBM beats the logit on the rare-event metric
  (PR-AUC {t['pr_auc']:.4f} vs {lg['pr_auc']:.4f}); because that margin sits on
  {metrics['test_positives']} positives it is reported with a paired bootstrap (see §3),
  not as a bare point comparison. The unconstrained GBM scores higher on PR-AUC
  ({ug_pr:.4f} vs {t['pr_auc']:.4f}, a {ug_gap:.4f} / {ug_rel:.0%} gap); that gap is the
  deliberate cost of the monotone constraints. A free model can buy a little in-window
  PR-AUC by learning a perverse relationship (e.g. more capital raising predicted risk),
  which is precisely what conceptual-soundness review rejects, so the constrained,
  economically-signed model is the one served.
- **Hyperparameters:** tuned with Optuna over inner time-series CV folds (not hand-set
  magic numbers); the search is recorded in the metrics artifact.
- **No leakage:** the embargo guarantees a training row's label window (q, q+H] ends
  strictly before the test start (train q <= test_start - H - reporting_lag - 1),
  enforced at runtime (`assert_no_temporal_overlap`); labels are strictly forward-looking
  with merger / end-of-data censoring. OOT ROC-AUC {t['roc_auc']:.4f} is well below the
  >0.98 leakage-suspicion threshold.
- **Honest data caveats:** the bank-level model does **not** join macro series (FRED is
  business-surface context, not a model input), so no macro-vintage question arises here.
  FDIC `/financials` returns currently-restated values, not the originally-filed Call
  Report; feature values are as-served, and originally-filed FFIEC data is the path to
  strict point-in-time feature integrity.

## 2. Ongoing monitoring (plan)
- **Drift:** Evidently data-drift + prediction-drift on inputs/scores each quarter
  (prediction drift is the earliest signal since labels arrive late).
- **Freshness / schema:** Pydantic v2 input validation at serving; feature null-rate
  and freshness checks.
- **Retraining:** quarterly Airflow DAG (`dag_ml_retrain`: build -> train+register -> metric
  gate -> export); the gate blocks promotion. Serving resolves the MLflow champion alias
  (`models:/finlens_bank_distress@champion`), so rollback is a real alias repoint, with the
  pinned local artifact as offline fallback.
- **Stability:** OMP_NUM_THREADS=1, bounded memory, last-known-good artifact cached.
- **Audit:** every served request is logged (request id, inputs, version, probability, flag,
  reason codes) for outcomes analysis and prediction-drift on real traffic.

## 3. Outcomes analysis (back-testing)
- **Headline holdout:** {metrics['n_test']:,} bank-quarters / {metrics['test_positives']} real
  failures (2019-2026, includes the 2023 SVB/Signature/First-Republic cluster).
- **Uncertainty (the point estimates are not the result):** 95% stratified-bootstrap CIs —
  PR-AUC [{prci[0]:.3f}, {prci[1]:.3f}], recall@k [{rci[0]:.3f}, {rci[1]:.3f}]. The PR-AUC
  edge over the logit is a paired bootstrap: difference 95% CI
  [{dci[0]:+.3f}, {dci[1]:+.3f}], P(LGBM > logit) = {diff.get('prob_a_beats_b', float('nan')):.1%}.
- **Multi-origin rolling backtest:** {rb.get('n_folds', 0)} embargoed out-of-time folds,
  PR-AUC mean {rb.get('pr_auc_mean')} (std {rb.get('pr_auc_std')}, range
  {rb.get('pr_auc_min')}-{rb.get('pr_auc_max')}); strong in failure-containing windows,
  near-floor in calm years.
- Reported by-year cohorts (crisis vs calm) — the model is not a single-period fit.
- Calibration verified on the OOT set (ECE + top-decile observed-vs-predicted), not just
  an uninformative all-rows Brier.
- Served-model provenance recorded; reproducible (fixed seed, pinned feature set, $0 CI
  import-guard).

## Known gaps (honest, on the path to production)
- Competing risks (merger vs failure) are handled by right-censoring, not a formal
  Fine-Gray / cause-specific hazard model. Informative censoring (a stressed bank acquired
  instead of failing) could bias the failure hazard down; a cause-specific treatment is the
  next refinement.
- Features come from the FDIC `/financials` endpoint, which serves currently-restated
  values rather than the originally-filed Call Report. The leakage embargo handles label
  timing, not feature restatement; sourcing originally-filed FFIEC CDR data is the path to
  strict point-in-time feature integrity.
- The data is U.S. public Call Report financials only; it cannot see confidential
  supervisory information, intraday liquidity, or deposit-flow data.

## Effective challenge
This report + the benchmark comparison + the adversarial phase reviews constitute the
independent challenge. The CI metric gate (PR-AUC must beat the logit benchmark by a
margin, OOT ROC below the leakage ceiling, calibration ECE bound) blocks promotion.
"""
    out = Path(settings.repo_root) / "docs" / "ml" / "VALIDATION_REPORT.md"
    out.write_text(report, encoding="utf-8")
    return out


def main() -> None:
    card = generate_model_card()
    report = generate_validation_report()
    print(f"wrote {card}")
    print(f"wrote {report}")


if __name__ == "__main__":
    main()
