"""Measurement experiment for the ML max-out effort (Tier A).

Does NOT ship anything. It measures, on the SAME out-of-time protocol the shipped
model uses (final_holdout_split, 28q), what each Tier-A technique actually buys:

  baseline (current shipped recipe, light tune) ->
  heavy Optuna tune ->
  seed-bagging (K seeds averaged) ->
  simple-average blend (monotone + unconstrained + logit) ->
  logit stack (OOF meta-learner).

Each is reported with a 95% bootstrap PR-AUC CI so we can apply the acceptance
rule (a technique ships only if its CI lower bound >= baseline point estimate).
Reproducible: fixed seed, pinned features, $0.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
for p in (REPO, REPO / "src", REPO / "ml"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from finlens_ml.config import get_ml_settings  # noqa: E402
from finlens_ml.evaluate import bootstrap_metrics, evaluate  # noqa: E402
from finlens_ml.features import FEATURE_COLUMNS  # noqa: E402
from finlens_ml.splits import final_holdout_split, rolling_origin_folds  # noqa: E402
from finlens_ml.train import (  # noqa: E402
    _fit_calibrated,
    _fit_logit,
    _tune_hyperparameters,
    load_dataset,
)

SEED = 42
HORIZON = 4
HOLDOUT_Q = 28


def _ci(y, p, k):
    m = evaluate(y, p, k=k)
    b = bootstrap_metrics(y, p, k=k, n_boot=2000, seed=SEED)
    lo, hi = b.get("pr_auc_ci", [float("nan"), float("nan")])
    return {"pr_auc": round(float(m.pr_auc), 4), "ci": [round(lo, 4), round(hi, 4)],
            "roc_auc": round(float(m.roc_auc), 4), "recall_at_k": round(float(m.recall_at_k), 4)}


def main() -> None:
    t0 = time.time()
    settings = get_ml_settings()
    k = settings.review_budget_k
    lag = settings.reporting_lag_q
    label = f"label_{HORIZON}"

    df = load_dataset()
    df = df[df[label].notna()].reset_index(drop=True).copy()
    df[label] = df[label].astype(int)
    X = df[FEATURE_COLUMNS].astype(float)
    y = df[label].to_numpy()
    obs = df["obs_qord"]

    tr_idx, te_idx = final_holdout_split(
        obs, horizon_q=HORIZON, holdout_quarters=HOLDOUT_Q, reporting_lag_q=lag
    )
    X_tr, y_tr = X.iloc[tr_idx].reset_index(drop=True), y[tr_idx]
    X_te, y_te = X.iloc[te_idx].reset_index(drop=True), y[te_idx]
    obs_tr = obs.iloc[tr_idx].reset_index(drop=True)
    print(f"train={len(tr_idx):,} ({y_tr.sum()} pos)  holdout={len(te_idx):,} "
          f"({y_te.sum()} pos)", flush=True)

    out: dict = {"protocol": "final_holdout_split", "holdout_quarters": HOLDOUT_Q,
                 "test_positives": int(y_te.sum()), "k": k, "results": {}}

    # ---- 0. baseline: light tune (15 trials / 3 folds), current recipe ----
    print("[0] baseline light tune (15 trials)...", flush=True)
    bp0, info0 = _tune_hyperparameters(X_tr, y_tr, obs_tr, HORIZON, SEED,
                                       reporting_lag_q=lag, n_trials=15, timeout=300)
    _, cal0, *_ = _fit_calibrated(X_tr, y_tr, SEED, params=bp0)
    p0 = cal0.predict_proba(X_te)[:, 1]
    out["results"]["baseline_light"] = {**_ci(y_te, p0, k), "tune": info0}
    print("    baseline:", out["results"]["baseline_light"]["pr_auc"],
          out["results"]["baseline_light"]["ci"], flush=True)

    # ---- 1. heavy tune (200 trials / up to 6 folds) ----
    print("[1] heavy Optuna tune (200 trials)...", flush=True)
    bp1, info1 = _tune_hyperparameters(X_tr, y_tr, obs_tr, HORIZON, SEED,
                                       reporting_lag_q=lag, n_trials=120, timeout=700)
    _, cal1, *_ = _fit_calibrated(X_tr, y_tr, SEED, params=bp1)
    p1 = cal1.predict_proba(X_te)[:, 1]
    out["results"]["heavy_tune"] = {**_ci(y_te, p1, k), "tune": info1}
    print("    heavy_tune:", out["results"]["heavy_tune"]["pr_auc"],
          out["results"]["heavy_tune"]["ci"], flush=True)

    # ---- 2. seed-bagging on the heavy-tuned params (K seeds) ----
    print("[2] seed-bagging (12 seeds)...", flush=True)
    preds = []
    for s in range(12):
        _, cal_s, *_ = _fit_calibrated(X_tr, y_tr, SEED + s, params=bp1)
        preds.append(cal_s.predict_proba(X_te)[:, 1])
    p_bag = np.mean(preds, axis=0)
    out["results"]["bagged"] = {**_ci(y_te, p_bag, k), "n_seeds": len(preds)}
    print("    bagged:", out["results"]["bagged"]["pr_auc"],
          out["results"]["bagged"]["ci"], flush=True)

    # ---- 3. simple-average blend (monotone + unconstrained + logit), no training ----
    print("[3] simple-average blend...", flush=True)
    _, cal_unc, *_ = _fit_calibrated(X_tr, y_tr, SEED, params=bp1, monotone=False)
    logit = _fit_logit(X_tr, y_tr)
    p_unc = cal_unc.predict_proba(X_te)[:, 1]
    p_log = logit.predict_proba(X_te)[:, 1]
    p_blend = np.mean([p_bag, p_unc, p_log], axis=0)
    out["results"]["blend_avg"] = _ci(y_te, p_blend, k)
    print("    blend_avg:", out["results"]["blend_avg"]["pr_auc"],
          out["results"]["blend_avg"]["ci"], flush=True)

    # ---- 4. logit stack via OOF on inner rolling folds (no leakage) ----
    print("[4] logit stack (OOF meta)...", flush=True)
    folds = rolling_origin_folds(obs_tr, horizon_q=HORIZON, min_train_quarters=24,
                                 step=4, n_test_quarters=4, reporting_lag_q=lag)
    folds = [f for f in folds if y_tr[f.test_idx].sum() >= 1 and y_tr[f.train_idx].sum() >= 20]
    oof_idx, oof_mono, oof_unc, oof_log, oof_y = [], [], [], [], []
    for f in folds:
        ytr_f = y_tr[f.train_idx]
        _, cm, *_ = _fit_calibrated(X_tr.iloc[f.train_idx], ytr_f, SEED, params=bp1)
        _, cu, *_ = _fit_calibrated(X_tr.iloc[f.train_idx], ytr_f, SEED, params=bp1, monotone=False)
        lg = _fit_logit(X_tr.iloc[f.train_idx], ytr_f)
        oof_mono.append(cm.predict_proba(X_tr.iloc[f.test_idx])[:, 1])
        oof_unc.append(cu.predict_proba(X_tr.iloc[f.test_idx])[:, 1])
        oof_log.append(lg.predict_proba(X_tr.iloc[f.test_idx])[:, 1])
        oof_y.append(ytr_f[None] if False else y_tr[f.test_idx])
        oof_idx.append(f.test_idx)
    if folds:
        from sklearn.linear_model import LogisticRegression
        Z = np.column_stack([np.concatenate(oof_mono), np.concatenate(oof_unc),
                             np.concatenate(oof_log)])
        zy = np.concatenate(oof_y)
        meta = LogisticRegression(class_weight="balanced", max_iter=2000)
        meta.fit(Z, zy)
        Zte = np.column_stack([p_bag, p_unc, p_log])
        p_stack = meta.predict_proba(Zte)[:, 1]
        out["results"]["stack_logit"] = {**_ci(y_te, p_stack, k),
                                         "meta_coef": [round(float(c), 3) for c in meta.coef_[0]]}
        print("    stack_logit:", out["results"]["stack_logit"]["pr_auc"],
              out["results"]["stack_logit"]["ci"], "coef", out["results"]["stack_logit"]["meta_coef"],
              flush=True)

    out["elapsed_sec"] = round(time.time() - t0, 1)
    dest = settings.artifact_dir / "maxout_experiment.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwrote {dest} in {out['elapsed_sec']}s", flush=True)
    base = out["results"]["baseline_light"]["pr_auc"]
    print(f"\n== SUMMARY (baseline PR-AUC {base}) ==", flush=True)
    for name, r in out["results"].items():
        flag = "" if name == "baseline_light" else (" SHIPS" if r["ci"][0] >= base else " (no)")
        print(f"  {name:16s} PR-AUC {r['pr_auc']}  CI {r['ci']}{flag}", flush=True)


if __name__ == "__main__":
    main()
