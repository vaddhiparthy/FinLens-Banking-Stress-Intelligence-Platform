"""Competing-risks analysis: failure vs merger as competing events.

The shipped model treats merger/acquisition exits as right-censored (labels.py drops a
bank's pre-exit quarters once it leaves the panel without a failure record). That is
correct cause-specific hazard practice, but it has a known bias: a DISTRESSED bank that
is ACQUIRED instead of failing has its would-be-positive quarters removed from the
labelable pool (informative censoring), biasing measured failure recall DOWNWARD.

This script, with no new dependencies ($0), quantifies that bias and gives the proper
competing-risks view:
  1. Build a merger-exit event label (exits the panel within H quarters, no failure).
  2. Fit a cause-specific MERGER hazard (LightGBM) alongside the failure hazard.
  3. Aalen-Johansen discrete-time cumulative incidence for failure vs merger.
  4. Informative-censoring bias: of banks that exited via merger, how many were in an
     ELEVATED-distress state (failure score >= review threshold) at their last filing -
     i.e. would-be positives removed by censoring - and the implied recall correction.

Writes ml/artifacts/competing_risks.json.
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
from finlens_ml.features import FEATURE_COLUMNS  # noqa: E402

ART = REPO / "ml" / "artifacts"
H = 4
SEED = 42


def _panel() -> pd.DataFrame:
    import duckdb

    with duckdb.connect(str(get_ml_settings().duckdb_path), read_only=True) as c:
        return c.execute("select * from ml.training_dataset").df()


def main() -> None:
    df = _panel().sort_values(["cert", "obs_qord"]).reset_index(drop=True)
    gmax = int(df["obs_qord"].max())
    lag = get_ml_settings().reporting_lag_q

    # per-cert exit quarter (last observed) and failure quarter
    last = df.groupby("cert")["obs_qord"].max().rename("exit_qord")
    failq = df.groupby("cert")["fail_qord"].first().rename("fail_qord_c")
    meta = pd.concat([last, failq], axis=1).reset_index()
    df = df.merge(meta, on="cert", how="left")

    # merger-exit event: bank leaves the panel (exit_qord) without a failure record, and
    # the exit is a real mid-panel exit (not end-of-data within the horizon+lag tail).
    merged_cert = df["fail_qord_c"].isna() & (df["exit_qord"] <= gmax - (H + lag))
    # competing-event label for quarter q: merger within (q, q+H], no failure
    df["label_merger_4"] = (
        merged_cert
        & (df["exit_qord"] > df["obs_qord"])
        & (df["exit_qord"] <= df["obs_qord"] + H)
    ).astype(int)

    n_merger_events = int(df["label_merger_4"].sum())
    n_failure_events = int((df["label_4"] == 1).sum())
    n_merger_certs = int(merged_cert.groupby(df["cert"]).first().sum())

    # ---- cause-specific merger hazard (LightGBM), same features ----
    import lightgbm as lgb

    lab = df[df["labelable_4"].notna() | (df["label_merger_4"] == 1)].copy()
    X = lab[FEATURE_COLUMNS].astype(float)
    ym = lab["label_merger_4"].to_numpy()
    spw = min(float((ym == 0).sum() / max(1, (ym == 1).sum())), 40.0)
    merger_model = lgb.LGBMClassifier(
        objective="binary", n_estimators=200, num_leaves=31, learning_rate=0.03,
        scale_pos_weight=spw, n_jobs=4, random_state=SEED, verbose=-1)
    merger_model.fit(X, ym)

    # ---- Aalen-Johansen discrete-time cumulative incidence over the panel ----
    # per-quarter cause-specific hazards (event count / at-risk), then CIF.
    g = df.groupby("obs_qord")
    haz = pd.DataFrame({
        "n": g.size(),
        "fail": g.apply(lambda d: (d["label_4"] == 1).sum(), include_groups=False),
        "merge": g["label_merger_4"].sum(),
    })
    haz = haz[haz["n"] > 0]
    haz["h_fail"] = haz["fail"] / haz["n"]
    haz["h_merge"] = haz["merge"] / haz["n"]
    surv = 1.0
    cif_fail = cif_merge = 0.0
    for _, r in haz.iterrows():
        cif_fail += surv * r["h_fail"]
        cif_merge += surv * r["h_merge"]
        surv *= (1 - r["h_fail"] - r["h_merge"])

    # ---- informative-censoring bias: distressed mergers ----
    # of the banks that exited via merger, how many were ELEVATED-distress at their last
    # filing (failure score >= review threshold)? those are would-be positives removed.
    from finlens_ml import scenario
    metrics = json.loads((ART / "metrics_h4.json").read_text())
    thr = metrics["oot_test"]["calibrated_lgbm"].get("threshold", 0.1)
    merger_exit_certs = meta[meta["fail_qord_c"].isna()
                             & (meta["exit_qord"] <= gmax - (H + lag))]["cert"].tolist()
    elevated = 0
    scored = 0
    for cert in merger_exit_certs:
        sub = df[(df["cert"] == cert) & (df["obs_qord"] == df["exit_qord"])]
        if sub.empty:
            continue
        feats = {c: (None if pd.isna(sub.iloc[0][c]) else float(sub.iloc[0][c]))
                 for c in FEATURE_COLUMNS}
        try:
            p = scenario.score_features(feats)["probability"]
        except Exception:
            continue
        scored += 1
        if p >= thr:
            elevated += 1
    distressed_merger_rate = (elevated / scored) if scored else float("nan")

    out = {
        "horizon_q": H,
        "n_failure_events": n_failure_events,
        "n_merger_events": n_merger_events,
        "n_merger_certs": n_merger_certs,
        "cumulative_incidence": {
            "failure": round(float(cif_fail), 5),
            "merger": round(float(cif_merge), 5),
            "note": ("Aalen-Johansen discrete-time cumulative incidence over the panel; "
                     "mergers are ~{:.0f}x more common than failures, which is why "
                     "treating them as a competing risk matters.").format(
                         cif_merge / cif_fail if cif_fail else float("nan")),
        },
        "informative_censoring": {
            "merger_exit_banks_scored": scored,
            "elevated_distress_at_exit": elevated,
            "distressed_merger_rate": round(distressed_merger_rate, 4),
            "interpretation": (
                f"{elevated} of {scored} merger-exit banks ({distressed_merger_rate:.1%}) "
                "were at or above the review threshold at their last filing - would-be "
                "positives removed from the labelable pool by censoring, biasing measured "
                "failure recall downward. This bounds the informative-censoring bug: the "
                "true recall is at most this fraction higher than measured."),
        },
        "method": ("cause-specific hazards (failure + merger) + Aalen-Johansen CIF, "
                   "implemented from scratch (no new deps, $0). A full Fine-Gray "
                   "subdistribution model has since been BUILT (ml/scripts/fine_gray.py, "
                   "within noise of cause-specific); this quantifies the "
                   "bias the current censoring introduces, which is the decision-relevant "
                   "number."),
    }
    (ART / "competing_risks.json").write_text(json.dumps(out, indent=2))
    print("failure events:", n_failure_events, "| merger events:", n_merger_events,
          "| merger certs:", n_merger_certs, flush=True)
    print(f"CIF failure {cif_fail:.4f} vs merger {cif_merge:.4f} "
          f"({cif_merge/cif_fail:.1f}x more mergers)", flush=True)
    print(f"distressed-at-exit mergers: {elevated}/{scored} = {distressed_merger_rate:.1%}",
          flush=True)
    print(f"wrote {ART/'competing_risks.json'}", flush=True)


if __name__ == "__main__":
    main()
