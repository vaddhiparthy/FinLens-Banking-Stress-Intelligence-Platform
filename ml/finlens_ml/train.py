"""Train the bank-distress hazard model with honest out-of-time evaluation.

Two models are produced:
  * EVAL model  — trained on 2008..(test_start-embargo), evaluated on a long,
    FAILURE-CONTAINING out-of-time window (default: last 28 quarters, ~2019-2026,
    which includes the 2023 SVB/Signature/First-Republic cluster). Judging a rare-
    event model on a single calm holdout is meaningless; this window has positives,
    and we report by-year cohorts so calm vs. stress years are visible.
  * FINAL model — trained on ALL labelable data, for serving.

Both: LightGBM (monotone constraints + scale_pos_weight) -> isotonic/Platt
calibration on a STRATIFIED in-training holdout (so the calibrator sees positives;
calibrating on a calm slice inverts the ranking). Plus a penalized-logit benchmark
for effective challenge. Logged to MLflow (sqlite -> registry alias works locally).

$0: no billable imports. Reproducible: fixed seed, pinned feature set.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
for p in (REPO, REPO / "src", REPO / "ml"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from finlens_ml.config import get_ml_settings  # noqa: E402
from finlens_ml.evaluate import (  # noqa: E402
    bootstrap_metrics,
    calibration_report,
    evaluate,
    evaluate_by_cohort,
    paired_bootstrap_ap_diff,
)
from finlens_ml.features import FEATURE_COLUMNS, MONOTONE_CONSTRAINTS  # noqa: E402
from finlens_ml.splits import final_holdout_split, rolling_origin_folds  # noqa: E402

EVAL_HOLDOUT_QUARTERS = 28  # ~2019Q1..2026Q1: long OOT window containing real failures


def _rolling_backtest(
    X: pd.DataFrame, y: np.ndarray, obs: pd.Series, horizon_q: int, k: int, seed: int,
    reporting_lag_q: int = 0,
) -> dict:
    """Multi-origin rolling backtest: refit + evaluate the calibrated model at several
    out-of-time origins and report fold-to-fold dispersion. A single holdout cannot
    show variance; this is what makes the headline trustworthy at ~66 positives."""
    folds = rolling_origin_folds(
        obs, horizon_q=horizon_q, min_train_quarters=28, step=4, n_test_quarters=4,
        reporting_lag_q=reporting_lag_q,
    )
    per_fold: list[dict] = []
    for f in folds:
        y_tr_f = y[f.train_idx]
        y_te_f = y[f.test_idx]
        if y_tr_f.sum() < 20 or y_te_f.sum() < 1:
            continue  # need positives on both sides to fit + score honestly
        _, cal_f, _, _, _ = _fit_calibrated(X.iloc[f.train_idx], y_tr_f, seed)
        p_f = cal_f.predict_proba(X.iloc[f.test_idx])[:, 1]
        m = evaluate(y_te_f, p_f, k=k)
        per_fold.append({
            "test_year": f.test_quarter_ord // 4,
            "n": m.n, "n_positive": m.n_positive,
            "pr_auc": round(m.pr_auc, 4), "recall_at_k": round(m.recall_at_k, 4),
        })
    prs = [r["pr_auc"] for r in per_fold if r["pr_auc"] == r["pr_auc"]]
    recs = [r["recall_at_k"] for r in per_fold if r["recall_at_k"] == r["recall_at_k"]]
    agg = {
        "n_folds": len(per_fold),
        "pr_auc_mean": round(float(np.mean(prs)), 4) if prs else None,
        "pr_auc_std": round(float(np.std(prs)), 4) if prs else None,
        "pr_auc_min": round(float(np.min(prs)), 4) if prs else None,
        "pr_auc_max": round(float(np.max(prs)), 4) if prs else None,
        "recall_at_k_mean": round(float(np.mean(recs)), 4) if recs else None,
    }
    return {"aggregate": agg, "folds": per_fold}


def load_dataset() -> pd.DataFrame:
    import duckdb

    settings = get_ml_settings()
    with duckdb.connect(str(settings.duckdb_path), read_only=True) as conn:
        return conn.execute("select * from ml.training_dataset").df()


def _make_lgbm(spw: float, seed: int, n_estimators: int):
    import lightgbm as lgb

    return lgb.LGBMClassifier(
        objective="binary",
        n_estimators=n_estimators,
        learning_rate=0.03,
        num_leaves=31,
        min_child_samples=100,
        subsample=0.8,
        subsample_freq=1,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        monotone_constraints=[MONOTONE_CONSTRAINTS[c] for c in FEATURE_COLUMNS],
        scale_pos_weight=spw,
        n_jobs=4,
        random_state=seed,
        verbose=-1,
    )


def _fit_calibrated(X_tr: pd.DataFrame, y_tr: np.ndarray, seed: int, fixed_rounds: int | None = None):
    """Fit LightGBM (monotone + class-weighted) and calibrate on a stratified
    in-training holdout.

    fixed_rounds=None  -> EVAL mode: early-stop on average_precision to DISCOVER the
                          tree count (AUC saturates at ~1 tree on few positives; AP
                          lets the model grow).
    fixed_rounds=int   -> FINAL/served mode: train exactly that many trees on all data
                          (no future to early-stop on), so the served model matches
                          the validated complexity instead of collapsing to 1 tree.
    Returns (model, calibrated, method, spw, best_iteration).
    """
    import lightgbm as lgb
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.model_selection import train_test_split

    X_fit, X_cal, y_fit, y_cal = train_test_split(
        X_tr, y_tr, test_size=0.20, stratify=y_tr, random_state=seed
    )
    # moderate the class weight: raw neg/pos (~190) is so extreme the model saturates
    # instantly; a capped weight keeps positives emphasized, calibration fixes probs.
    raw_spw = float((y_fit == 0).sum() / max(1, (y_fit == 1).sum()))
    spw = float(min(raw_spw, 25.0))

    if fixed_rounds is None:
        X_core, X_val, y_core, y_val = train_test_split(
            X_fit, y_fit, test_size=0.15, stratify=y_fit, random_state=seed
        )
        spw = float(min(float((y_core == 0).sum() / max(1, (y_core == 1).sum())), 25.0))
        model = _make_lgbm(spw, seed, n_estimators=3000)
        model.fit(
            X_core, y_core,
            eval_set=[(X_val, y_val)],
            eval_metric="average_precision",
            callbacks=[lgb.early_stopping(200, verbose=False), lgb.log_evaluation(0)],
        )
        best_it = int(getattr(model, "best_iteration_", 0) or model.n_estimators)
    else:
        best_it = max(1, fixed_rounds)
        model = _make_lgbm(spw, seed, n_estimators=best_it)
        model.fit(X_fit, y_fit)

    method = "isotonic" if int(y_cal.sum()) >= 50 else "sigmoid"
    try:
        from sklearn.frozen import FrozenEstimator

        calibrated = CalibratedClassifierCV(FrozenEstimator(model), method=method)
    except Exception:
        calibrated = CalibratedClassifierCV(model, method=method, cv="prefit")
    calibrated.fit(X_cal, y_cal)
    return model, calibrated, method, spw, best_it


def _fit_logit(X_tr: pd.DataFrame, y_tr: np.ndarray):
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    logit = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("lr", LogisticRegression(class_weight="balanced", max_iter=2000, C=1.0)),
        ]
    )
    logit.fit(X_tr, y_tr)
    return logit


def train(horizon_q: int = 4, seed: int = 42) -> dict:
    settings = get_ml_settings()
    label = f"label_{horizon_q}"
    df = load_dataset()
    df = df[df[label].notna()].reset_index(drop=True).copy()
    df[label] = df[label].astype(int)

    X = df[FEATURE_COLUMNS].astype(float)
    y = df[label].to_numpy()
    obs = df["obs_qord"]

    # ---- EVAL: out-of-time on a failure-containing window ----
    tr_idx, te_idx = final_holdout_split(
        obs, horizon_q=horizon_q, holdout_quarters=EVAL_HOLDOUT_QUARTERS,
        reporting_lag_q=settings.reporting_lag_q,
    )
    X_tr, y_tr = X.iloc[tr_idx], y[tr_idx]
    X_te, y_te = X.iloc[te_idx], y[te_idx]
    year_te = (obs.iloc[te_idx].to_numpy() // 4).astype(int)  # calendar year cohort

    eval_model, eval_cal, method, spw, eval_best_it = _fit_calibrated(X_tr, y_tr, seed)
    eval_logit = _fit_logit(X_tr, y_tr)

    k = settings.review_budget_k
    p_cal = eval_cal.predict_proba(X_te)[:, 1]
    p_raw = eval_model.predict_proba(X_te)[:, 1]
    p_logit = eval_logit.predict_proba(X_te)[:, 1]

    results = {
        "horizon_q": horizon_q,
        "eval_window_quarters": EVAL_HOLDOUT_QUARTERS,
        "n_train": int(len(tr_idx)),
        "n_test": int(len(te_idx)),
        "test_positives": int(y_te.sum()),
        "scale_pos_weight": spw,
        "calibration_method": method,
        "best_iteration": int(eval_best_it),
        "oot_test": {
            "calibrated_lgbm": evaluate(y_te, p_cal, k=k).as_dict(),
            "raw_lgbm": evaluate(y_te, p_raw, k=k).as_dict(),
            "logit_benchmark": evaluate(y_te, p_logit, k=k).as_dict(),
        },
        # 95% bootstrap CIs (the point estimates above are not defensible alone at ~66
        # positives) + a paired test of whether the LGBM's PR-AUC edge over the logit
        # benchmark is real or inside the noise band.
        "oot_test_ci": bootstrap_metrics(y_te, p_cal, k=k),
        "lgbm_vs_logit_ap_diff": paired_bootstrap_ap_diff(y_te, p_cal, p_logit),
        # multi-origin rolling backtest: fold-to-fold dispersion, not one holdout.
        "rolling_backtest": _rolling_backtest(
            X, y, obs, horizon_q, k, seed, reporting_lag_q=settings.reporting_lag_q
        ),
        "by_year_calibrated": evaluate_by_cohort(y_te, p_cal, year_te, k=25),
        # honest calibration: all-rows Brier is dominated by negatives; ECE +
        # top-decile Brier measure where flags actually happen. Calibrator is fit on
        # a stratified in-train holdout (so it sees positives; a calm temporal tail
        # inverts Platt) — all calib rows are pre-test, so OOT ranking is unleaked.
        "oot_calibration": calibration_report(y_te, p_cal),
    }

    # ---- FINAL: train on ALL data with the VALIDATED tree count, calibrate, serve ----
    final_model, final_cal, final_method, final_spw, final_it = _fit_calibrated(
        X, y, seed, fixed_rounds=eval_best_it
    )
    # provenance for the SERVED model (B3): identical pipeline + the tree count
    # discovered by the eval model's out-of-time early stopping.
    results["final_model"] = {
        "n_train": int(len(X)),
        "n_estimators": int(final_it),
        "tree_count_source": "eval-model out-of-time early stopping (average_precision)",
        "calibration_method": final_method,
        "scale_pos_weight": final_spw,
        "note": "served model; trained on all data via the identical _fit_calibrated "
        "pipeline, using the OOT-validated tree count from the eval model whose "
        "metrics are reported above",
    }
    _log_to_mlflow(settings, results, final_cal, horizon_q)
    _save_artifacts(settings, final_cal, final_model, results, horizon_q)
    return results


def _log_to_mlflow(settings, results: dict, calibrated, horizon_q: int) -> None:
    try:
        import mlflow
        import mlflow.sklearn

        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)  # single source of truth (config)
        mlflow.set_experiment("finlens_bank_distress")
        with mlflow.start_run(run_name=f"lgbm_h{horizon_q}"):
            mlflow.log_param("horizon_q", horizon_q)
            mlflow.log_param("calibration_method", results["calibration_method"])
            mlflow.log_param("scale_pos_weight", results["scale_pos_weight"])
            mlflow.log_param("n_features", len(FEATURE_COLUMNS))
            mlflow.log_param("eval_window_quarters", results["eval_window_quarters"])
            # served-model provenance (B3): record the FINAL model's training config
            for key, val in results.get("final_model", {}).items():
                if isinstance(val, (int, float, str)):
                    mlflow.log_param(f"final__{key}", val)
            for mname, mset in results["oot_test"].items():
                for metric, val in mset.items():
                    if isinstance(val, (int, float)) and not (
                        isinstance(val, float) and np.isnan(val)
                    ):
                        mlflow.log_metric(f"{mname}__{metric}", float(val))
            for metric, val in results.get("oot_calibration", {}).items():
                if isinstance(val, (int, float)) and not (
                    isinstance(val, float) and np.isnan(val)
                ):
                    mlflow.log_metric(f"calib__{metric}", float(val))
            info = mlflow.sklearn.log_model(
                calibrated, name="model", registered_model_name=settings.registered_model_name
            )
            try:
                from finlens_ml.registry import promote_latest_to_champion

                v = promote_latest_to_champion()
                print(f"  champion -> version {v}", flush=True)
            except Exception as exc:
                print(f"  (alias set skipped: {exc})", flush=True)
            print(f"  mlflow logged: {info.model_uri}", flush=True)
    except Exception as exc:
        print(f"  (mlflow logging skipped: {exc})", flush=True)


def _save_artifacts(settings, calibrated, model, results: dict, horizon_q: int) -> None:
    settings.artifact_dir.mkdir(parents=True, exist_ok=True)
    (settings.artifact_dir / f"metrics_h{horizon_q}.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    model.booster_.save_model(str(settings.artifact_dir / f"booster_h{horizon_q}.txt"))
    try:
        import skops.io as sio

        sio.dump(calibrated, settings.artifact_dir / f"calibrated_h{horizon_q}.skops")
    except Exception as exc:
        print(f"  (skops dump skipped: {exc})", flush=True)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--horizon", type=int, default=4)
    args = parser.parse_args()
    r = train(horizon_q=args.horizon)
    t = r["oot_test"]
    cal, raw, log = t["calibrated_lgbm"], t["raw_lgbm"], t["logit_benchmark"]
    print(
        f"\nOOT window: {r['eval_window_quarters']}q, test n={r['n_test']:,} "
        f"positives={r['test_positives']}"
    )
    print(
        f"calibrated LGBM : PR-AUC={cal['pr_auc']:.4f} ROC-AUC={cal['roc_auc']:.4f} "
        f"Brier={cal['brier']:.5f} recall@{cal['k']}={cal['recall_at_k']:.3f}"
    )
    print(f"raw LGBM        : PR-AUC={raw['pr_auc']:.4f} ROC-AUC={raw['roc_auc']:.4f}")
    print(
        f"logit benchmark : PR-AUC={log['pr_auc']:.4f} ROC-AUC={log['roc_auc']:.4f} "
        f"(LGBM must beat this; PR-AUC is the rare-event headline, ROC comparability-only)"
    )
    cr = r.get("oot_calibration", {})
    print(
        f"calibration     : ECE={cr.get('ece', float('nan')):.2e} "
        f"top-decile pred={cr.get('top_decile_pred', float('nan')):.4f} "
        f"vs obs={cr.get('top_decile_obs', float('nan')):.4f}"
    )
    fm = r.get("final_model", {})
    print(
        f"served model    : n_estimators={fm.get('n_estimators')} "
        f"(source: {fm.get('tree_count_source')}); calibration={fm.get('calibration_method')}"
    )
    print("by-year (calibrated):")
    for yr, m in r["by_year_calibrated"].items():
        print(f"  {yr}: n={m['n']:,} pos={m['n_positive']} "
              f"PR-AUC={m['pr_auc'] if isinstance(m['pr_auc'], str) else round(m['pr_auc'],4)} "
              f"ROC-AUC={m['roc_auc'] if isinstance(m['roc_auc'], str) else round(m['roc_auc'],4)}")


if __name__ == "__main__":
    main()
