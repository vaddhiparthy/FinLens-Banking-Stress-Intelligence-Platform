"""Finalize the served model with the BEST tuned config found by the controlled
200-trial-budget search (maxout_experiment.json), instead of a budget-truncated
re-search whose noisy pick can land below it. The Optuna search itself (from the
production retrain) is attached for the tuning visuals. Keeps served model, ablation,
and headline consistent at ~0.24.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
for p in (REPO, REPO / "src", REPO / "ml"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

ART = REPO / "ml" / "artifacts"


def main() -> None:
    exp = json.loads((ART / "maxout_experiment.json").read_text())
    ht = exp["results"]["heavy_tune"]["tune"]
    best = ht["best_params"]
    # the Optuna search captured by THIS experiment (same features as the served model),
    # for the tuning visuals (opt_history, importance, trial_stability, slices).
    study = ht.get("study", {})
    override = {"study": study, "cv_mean_pr_auc": ht.get("cv_mean_pr_auc"),
                "n_trials": ht.get("n_trials"), "n_inner_folds": ht.get("n_inner_folds")}

    from finlens_ml.train import train
    r = train(horizon_q=4, fixed_params=best, study_override=override, bagged_k=12)
    t = r["oot_test"]["calibrated_lgbm"]
    o = r["hyperparameter_tuning"].get("study", {}).get("optimism", {})
    print(f"served (best tuned config): OOT PR-AUC={t['pr_auc']:.4f} "
          f"ROC={t['roc_auc']:.4f} recall@200={t['recall_at_k']:.3f}", flush=True)
    print(f"optimism: inner {o.get('inner_pr_auc')} vs OOT {o.get('oot_pr_auc')} "
          f"ratio {o.get('ratio')}", flush=True)


if __name__ == "__main__":
    main()
