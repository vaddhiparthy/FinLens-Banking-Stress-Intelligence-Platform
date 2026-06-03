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
from finlens_ml.evaluate import evaluate, evaluate_by_cohort  # noqa: E402
from finlens_ml.features import FEATURE_COLUMNS, MONOTONE_CONSTRAINTS  # noqa: E402
from finlens_ml.splits import final_holdout_split  # noqa: E402

EVAL_HOLDOUT_QUARTERS = 28  # ~2019Q1..2026Q1: long OOT window containing real failures


def load_dataset() -> pd.DataFrame:
    import duckdb

    settings = get_ml_settings()
    with duckdb.connect(str(settings.duckdb_path), read_only=True) as conn:
        return conn.execute("select * from ml.training_dataset").df()


def _fit_calibrated(X_tr: pd.DataFrame, y_tr: np.ndarray, seed: int):
    """Fit LightGBM (monotone + class-weighted) and calibrate on a stratified
    in-training holdout. Returns (raw_model, calibrated_model, method, spw)."""
    import lightgbm as lgb
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.model_selection import train_test_split

    X_fit, X_cal, y_fit, y_cal = train_test_split(
        X_tr, y_tr, test_size=0.20, stratify=y_tr, random_state=seed
    )
    X_core, X_val, y_core, y_val = train_test_split(
        X_fit, y_fit, test_size=0.10, stratify=y_fit, random_state=seed
    )
    mc = [MONOTONE_CONSTRAINTS[c] for c in FEATURE_COLUMNS]
    spw = float((y_core == 0).sum() / max(1, (y_core == 1).sum()))
    model = lgb.LGBMClassifier(
        objective="binary",
        n_estimators=3000,
        learning_rate=0.02,
        num_leaves=31,
        min_child_samples=200,
        subsample=0.8,
        subsample_freq=1,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        monotone_constraints=mc,
        scale_pos_weight=spw,
        n_jobs=4,
        random_state=seed,
        verbose=-1,
    )
    model.fit(
        X_core, y_core,
        eval_set=[(X_val, y_val)],
        eval_metric="auc",
        callbacks=[lgb.early_stopping(100, verbose=False), lgb.log_evaluation(0)],
    )
    n_cal_pos = int(y_cal.sum())
    method = "isotonic" if n_cal_pos >= 50 else "sigmoid"
    try:
        from sklearn.frozen import FrozenEstimator

        calibrated = CalibratedClassifierCV(FrozenEstimator(model), method=method)
    except Exception:
        calibrated = CalibratedClassifierCV(model, method=method, cv="prefit")
    calibrated.fit(X_cal, y_cal)
    return model, calibrated, method, spw


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
        obs, horizon_q=horizon_q, holdout_quarters=EVAL_HOLDOUT_QUARTERS
    )
    X_tr, y_tr = X.iloc[tr_idx], y[tr_idx]
    X_te, y_te = X.iloc[te_idx], y[te_idx]
    year_te = (obs.iloc[te_idx].to_numpy() // 4).astype(int)  # calendar year cohort

    eval_model, eval_cal, method, spw = _fit_calibrated(X_tr, y_tr, seed)
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
        "best_iteration": int(getattr(eval_model, "best_iteration_", 0) or 0),
        "oot_test": {
            "calibrated_lgbm": evaluate(y_te, p_cal, k=k).as_dict(),
            "raw_lgbm": evaluate(y_te, p_raw, k=k).as_dict(),
            "logit_benchmark": evaluate(y_te, p_logit, k=k).as_dict(),
        },
        "by_year_calibrated": evaluate_by_cohort(y_te, p_cal, year_te, k=25),
    }

    # ---- FINAL: train on ALL data, calibrate, save + register for serving ----
    final_model, final_cal, _, _ = _fit_calibrated(X, y, seed)
    _log_to_mlflow(settings, results, final_cal, horizon_q)
    _save_artifacts(settings, final_cal, final_model, results, horizon_q)
    return results


def _log_to_mlflow(settings, results: dict, calibrated, horizon_q: int) -> None:
    try:
        import mlflow
        import mlflow.sklearn

        mlflow.set_tracking_uri(f"sqlite:///{(REPO / 'ml' / 'mlflow.db').as_posix()}")
        mlflow.set_experiment("finlens_bank_distress")
        with mlflow.start_run(run_name=f"lgbm_h{horizon_q}"):
            mlflow.log_param("horizon_q", horizon_q)
            mlflow.log_param("calibration_method", results["calibration_method"])
            mlflow.log_param("scale_pos_weight", results["scale_pos_weight"])
            mlflow.log_param("n_features", len(FEATURE_COLUMNS))
            mlflow.log_param("eval_window_quarters", results["eval_window_quarters"])
            for mname, mset in results["oot_test"].items():
                for metric, val in mset.items():
                    if isinstance(val, (int, float)) and not (
                        isinstance(val, float) and np.isnan(val)
                    ):
                        mlflow.log_metric(f"{mname}__{metric}", float(val))
            info = mlflow.sklearn.log_model(
                calibrated, name="model", registered_model_name=settings.registered_model_name
            )
            try:
                client = mlflow.tracking.MlflowClient()
                mv = client.search_model_versions(f"name='{settings.registered_model_name}'")
                latest = max(mv, key=lambda v: int(v.version))
                client.set_registered_model_alias(
                    settings.registered_model_name, settings.champion_alias, latest.version
                )
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
        f"(LGBM must beat this)"
    )
    print("by-year (calibrated):")
    for yr, m in r["by_year_calibrated"].items():
        print(f"  {yr}: n={m['n']:,} pos={m['n_positive']} "
              f"PR-AUC={m['pr_auc'] if isinstance(m['pr_auc'], str) else round(m['pr_auc'],4)} "
              f"ROC-AUC={m['roc_auc'] if isinstance(m['roc_auc'], str) else round(m['roc_auc'],4)}")


if __name__ == "__main__":
    main()
