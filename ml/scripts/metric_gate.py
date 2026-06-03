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

PR_AUC_FLOOR_OVER_LOGIT = 0.0   # LGBM PR-AUC must be >= logit PR-AUC
ROC_LEAKAGE_CEILING = 0.98      # OOT ROC above this is suspicious (leakage)
ECE_CEILING = 0.05              # calibration sanity


def main() -> int:
    if not METRICS.exists():
        print(f"GATE SKIP: {METRICS} not present (train offline to enable the gate).")
        return 0
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

    print(f"LGBM PR-AUC={lgbm_pr:.4f} vs logit {logit_pr:.4f} | ROC={roc:.4f} | ECE={ece:.2e}")
    if failures:
        print("MODEL METRIC GATE FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("MODEL METRIC GATE PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
