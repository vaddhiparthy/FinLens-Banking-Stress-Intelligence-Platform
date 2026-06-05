"""CI model-metric gate. Fails the build if the trained model regresses below bar.

Reads the committed real metrics (ml/artifacts/metrics_h4.json) and asserts:
  * the LGBM beats the logit benchmark on PR-AUC (the rare-event headline);
  * OOT ROC-AUC is below 0.98 (a higher value would signal leakage);
  * calibration ECE is within a sane bound.
Exits non-zero on any breach so a degraded/leaky model cannot merge.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
METRICS = REPO / "ml" / "artifacts" / "metrics_h4.json"

PR_AUC_FLOOR_OVER_LOGIT = 0.03  # LGBM must beat logit PR-AUC by a real margin
ROC_LEAKAGE_CEILING = 0.98      # OOT ROC above this is suspicious (leakage)
ECE_CEILING = 0.05              # calibration sanity
PAIRED_PROB_FLOOR = 0.90        # paired-bootstrap P(LGBM>logit): edge must be significant


def main() -> int:
    if not METRICS.exists():
        # the metrics file is committed; absence means it was deleted -> hard fail.
        print(f"GATE FAILED: {METRICS} not present (it is tracked and required).")
        return 1
    m = json.loads(METRICS.read_text())
    t = m["oot_test"]
    lgbm_pr = t["calibrated_lgbm"]["pr_auc"]
    logit_pr = t["logit_benchmark"]["pr_auc"]
    roc = t["calibrated_lgbm"]["roc_auc"]
    ece = m.get("oot_calibration", {}).get("ece", 0.0)

    failures = []
    if lgbm_pr < logit_pr + PR_AUC_FLOOR_OVER_LOGIT:
        failures.append(f"PR-AUC {lgbm_pr:.4f} does not beat logit {logit_pr:.4f}")
    if roc >= ROC_LEAKAGE_CEILING:
        failures.append(f"OOT ROC-AUC {roc:.4f} >= {ROC_LEAKAGE_CEILING} (leakage suspicion)")
    if ece > ECE_CEILING:
        failures.append(f"calibration ECE {ece:.4f} > {ECE_CEILING}")
    # the edge over the benchmark must be statistically real, not inside the noise band:
    diff = m.get("lgbm_vs_logit_ap_diff", {})
    p_beat = diff.get("prob_a_beats_b")
    if p_beat is not None and p_beat < PAIRED_PROB_FLOOR:
        failures.append(
            f"paired-bootstrap P(LGBM>logit)={p_beat:.2f} < {PAIRED_PROB_FLOOR} (edge not significant)"
        )

    print(f"LGBM PR-AUC={lgbm_pr:.4f} vs logit {logit_pr:.4f} | ROC={roc:.4f} | ECE={ece:.2e} "
          f"| P(LGBM>logit)={p_beat}")
    if failures:
        print("MODEL METRIC GATE FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("MODEL METRIC GATE PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
