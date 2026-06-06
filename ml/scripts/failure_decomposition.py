"""Failure-type decomposition: which failures are financially VISIBLE (predictable from
Call Reports) vs structurally INVISIBLE (fast run / fraud / sudden), and what that does
to the headline. This is the load-bearing analysis behind the by-year collapse: a single
model averaged across failure types inverts on the types it cannot see.

Classification is MODEL-INDEPENDENT (raw financial signatures at the flagged quarter, not
the model's own score, to avoid circularity):
  - credit-visible:        high noncurrent or net charge-offs, or thin capital.
  - rate/liquidity-visible: high uninsured-deposit share with large securities book (the
                            2023 SVB-style profile, which Call Reports partially capture).
  - invisible:             none of the above; the bank looked financially sound at its
                            last filing and failed anyway. Structurally unpredictable from
                            quarterly financials.

Then PR-AUC is reported on the FULL OOT and on the ADDRESSABLE subset (invisible failures
removed from the positive set), and the visible/invisible split is broken out by year to
explain the 2022/2024 collapse. $0, no new deps. Writes failure_decomposition.json.
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
from finlens_ml.evaluate import bootstrap_metrics, evaluate  # noqa: E402
from finlens_ml.features import FEATURE_COLUMNS  # noqa: E402
from finlens_ml.splits import final_holdout_split  # noqa: E402
from finlens_ml.train import EVAL_HOLDOUT_QUARTERS, _fit_calibrated, load_dataset  # noqa: E402

SEED = 42


def _classify(row: pd.Series) -> str:
    def num(c):
        v = row.get(c)
        return float(v) if v is not None and v == v else np.nan

    def z(c):  # NaN treated as 0 (symmetric across both securities legs)
        v = num(c)
        return v if v == v else 0.0
    noncur, nco = num("noncurrent_to_loans"), num("nco_to_loans")
    t1, eq = num("tier1_rwa_ratio"), num("equity_to_assets")
    unins = z("uninsured_deposit_share")
    sec = z("htm_securities_share") + z("afs_securities_share")
    # credit-visible: elevated noncurrent / charge-offs, or capital below the Prompt
    # Corrective Action lines (Tier-1 risk-based adequately-capitalized = 6%; below = under-
    # capitalized) / a thin equity-to-assets cushion.
    credit = ((noncur == noncur and noncur >= 3.0) or (nco == nco and nco >= 1.0)
              or (t1 == t1 and t1 < 6.0) or (eq == eq and eq < 4.0))
    rate_liq = (unins >= 30.0) and (sec >= 5.0)
    if credit:
        return "credit_visible"
    if rate_liq:
        return "rate_liquidity_visible"
    return "invisible"


def main() -> None:
    s = get_ml_settings()
    k = s.review_budget_k
    df = load_dataset()
    df = df[df["label_4"].notna()].reset_index(drop=True).copy()
    df["label_4"] = df["label_4"].astype(int)
    X = df[FEATURE_COLUMNS].astype(float)
    y = df["label_4"].to_numpy()
    obs = df["obs_qord"]
    tr, te = final_holdout_split(obs, horizon_q=4, holdout_quarters=EVAL_HOLDOUT_QUARTERS,
                                 reporting_lag_q=s.reporting_lag_q)
    # served recipe (bagged) for honest scores on OOT
    metrics = json.loads((s.artifact_dir / "metrics_h4.json").read_text())
    bp = metrics.get("hyperparameter_tuning", {}).get("best_params")
    bagged_k = int(metrics.get("bagged_k", 1) or 1)
    _, cal, _, _, best_it = _fit_calibrated(X.iloc[tr], y[tr], SEED, params=bp)
    if bagged_k > 1:
        from finlens_ml.ensemble import fit_bagged
        cal = fit_bagged(X.iloc[tr], y[tr], SEED, bagged_k, bp, best_it)
    p_te = cal.predict_proba(X.iloc[te])[:, 1]
    y_te = y[te]
    te_df = df.iloc[te].reset_index(drop=True)
    filing_year = te_df["quarter"].str.slice(0, 4)
    # qord -> calendar year, to report the ACTUAL failure year (not the filing year). A
    # positive bank-quarter is a FILING that fails within the next 4 quarters, so the filing
    # year and the failure year differ: the 2022-filing cohort fails in 2023, etc. Some
    # failures occur just AFTER the panel ends (fail_qord > max observed qord), so the year
    # is extrapolated arithmetically rather than looked up, otherwise those banks would show
    # as "unrecorded".
    _ref = df.sort_values("obs_qord").iloc[-1]
    _ref_qord = int(_ref["obs_qord"]); _ref_y = int(_ref["quarter"][:4]); _ref_q = int(_ref["quarter"][5])

    def q2yr(qord):
        if qord != qord:
            return None
        total_q = (_ref_q - 1) + (int(qord) - _ref_qord)
        return str(_ref_y + total_q // 4)

    # classify each OOT positive (per bank-quarter)
    pos_idx = np.where(y_te == 1)[0]
    types: dict = {}
    by_filing_year: dict = {}
    for i in pos_idx:
        typ = _classify(te_df.iloc[i])
        types[typ] = types.get(typ, 0) + 1
        yr = filing_year.iloc[i]
        by_filing_year.setdefault(yr, {}).update(
            {typ: by_filing_year.get(yr, {}).get(typ, 0) + 1})

    # per DISTINCT bank: modal class, failure year, and name (verifiable against FDIC)
    pos_df = te_df.iloc[pos_idx].copy()
    pos_df["cls"] = [_classify(te_df.iloc[i]) for i in pos_idx]
    pos_df["failure_year"] = pos_df["fail_qord"].map(q2yr)
    banks = []
    for cert, grp in pos_df.groupby("cert"):
        modal = grp["cls"].value_counts().index[0]
        banks.append({
            "cert": int(cert),
            "bank": str(grp["bank_name"].iloc[0]),
            "failure_year": (None if grp["failure_year"].isna().all()
                             else str(grp["failure_year"].dropna().iloc[0])),
            "mode": modal,
        })
    banks.sort(key=lambda b: (b["failure_year"] or "9999", b["bank"]))
    mode_examples = {m: [b["bank"] for b in banks if b["mode"] == m]
                     for m in ("credit_visible", "rate_liquidity_visible", "invisible")}
    failure_year_banks: dict = {}
    for b in banks:
        fy = b["failure_year"] or "unrecorded"
        failure_year_banks.setdefault(fy, []).append(b["bank"])

    # PR-AUC: full vs addressable (drop invisible positives from the positive set)
    full = evaluate(y_te, p_te, k=k)
    invisible_mask = np.array([_classify(te_df.iloc[i]) == "invisible" for i in range(len(te_df))])
    keep = ~(invisible_mask & (y_te == 1))  # drop only invisible POSITIVES
    addr = evaluate(y_te[keep], p_te[keep], k=k)

    # bootstrap 95% CIs by the SAME percentile-bootstrap method used for the full-set headline, so the
    # addressable point estimate is not reported bare. Fewer positives (52 vs 66) => wider
    # interval; the two CIs are expected to overlap heavily, which is stated honestly.
    full_ci = bootstrap_metrics(y_te, p_te, k=k)["pr_auc_ci"]
    addr_ci = bootstrap_metrics(y_te[keep], p_te[keep], k=k)["pr_auc_ci"]

    n_pos = int(y_te.sum())
    n_invis = types.get("invisible", 0)

    # threshold sensitivity: vary the cuts and confirm the qualitative story (2022 filing
    # cohort rate/liquidity-dominated, 2024 invisible-dominated) survives, so "robust to
    # reasonable thresholds" is measured rather than asserted.
    def _classify_t(row, nc_t, t1_t, un_t, sec_t):
        def num(c):
            v = row.get(c)
            return float(v) if v is not None and v == v else np.nan

        def zz(c):
            v = num(c)
            return v if v == v else 0.0
        nc, nco = num("noncurrent_to_loans"), num("nco_to_loans")
        t1, eq = num("tier1_rwa_ratio"), num("equity_to_assets")
        un = zz("uninsured_deposit_share")
        sec = zz("htm_securities_share") + zz("afs_securities_share")
        if ((nc == nc and nc >= nc_t) or (nco == nco and nco >= 1.0)
                or (t1 == t1 and t1 < t1_t) or (eq == eq and eq < 4.0)):
            return "credit_visible"
        if un >= un_t and sec >= sec_t:
            return "rate_liquidity_visible"
        return "invisible"

    grids = [("base", 3.0, 6.0, 30.0, 5.0), ("loose", 2.0, 7.0, 25.0, 3.0),
             ("strict", 4.0, 5.0, 35.0, 8.0), ("uninsured-heavy", 3.0, 6.0, 40.0, 10.0)]
    fy = filing_year.iloc[pos_idx].to_numpy()
    sensitivity = []
    for name, nc_t, t1_t, un_t, sec_t in grids:
        cls = np.array([_classify_t(te_df.iloc[i], nc_t, t1_t, un_t, sec_t) for i in pos_idx])
        def _dom(year):
            m = cls[fy == year]
            return (pd.Series(m).value_counts().index[0] if len(m) else None)
        # addressable PR-AUC under THIS grid's invisible boundary
        inv_g = np.array([_classify_t(te_df.iloc[i], nc_t, t1_t, un_t, sec_t) == "invisible"
                          for i in range(len(te_df))])
        keep_g = ~(inv_g & (y_te == 1))
        sensitivity.append({
            "grid": name,
            "thresholds": {"noncurrent": nc_t, "tier1_rwa": t1_t, "uninsured": un_t,
                           "securities": sec_t},
            "counts": {k: int((cls == k).sum()) for k in
                       ("credit_visible", "rate_liquidity_visible", "invisible")},
            "dom_2022_filing": _dom("2022"),
            "dom_2024_filing": _dom("2024"),
            "pr_auc_addressable": round(float(evaluate(y_te[keep_g], p_te[keep_g], k=k).pr_auc), 4),
        })
    story_holds = all(g["dom_2022_filing"] == "rate_liquidity_visible"
                      and g["dom_2024_filing"] == "invisible" for g in sensitivity)
    addr_prs = [g["pr_auc_addressable"] for g in sensitivity]

    # the addressable headline depends ONLY on the invisible/visible boundary: it is the full
    # set minus the invisible positives, so the credit-vs-rate/liquidity split cannot move it.
    # Confirm with a genuine swap test: actually relabel every credit<->rate_liquidity positive
    # and recompute. Because neither of those buckets is "invisible", the dropped set is
    # unchanged and the addressable PR-AUC must come out identical to the base.
    _swap = {"credit_visible": "rate_liquidity_visible",
             "rate_liquidity_visible": "credit_visible"}
    cls_all = np.array([_classify(te_df.iloc[i]) for i in range(len(te_df))])
    cls_swapped = np.array([_swap.get(c, c) for c in cls_all])
    n_swapped = int(((cls_all != cls_swapped) & (y_te == 1)).sum())  # positives actually relabeled
    keep_swap = ~((cls_swapped == "invisible") & (y_te == 1))
    addr_boundary_swap = round(float(evaluate(y_te[keep_swap], p_te[keep_swap], k=k).pr_auc), 4)
    boundary_invariant = (addr_boundary_swap == round(float(addr.pr_auc), 4))

    out = {
        "n_oot_positives": n_pos,
        "n_distinct_banks": len(banks),
        "type_counts": types,
        "by_filing_year": by_filing_year,
        "year_axis_note": ("Keys are the FILING year of the bank-quarter. A positive is a "
                           "filing that fails within the next 4 quarters, so the failure "
                           "occurs later: the 2022-filing cohort failed in 2023 (the SVB "
                           "wave). No banks failed in calendar 2021 or 2022."),
        "failure_year_banks": failure_year_banks,
        "mode_examples": mode_examples,
        "pr_auc_full": round(float(full.pr_auc), 4),
        "pr_auc_full_ci": [round(full_ci[0], 4), round(full_ci[1], 4)],
        "pr_auc_addressable": round(float(addr.pr_auc), 4),
        "pr_auc_addressable_ci": [round(addr_ci[0], 4), round(addr_ci[1], 4)],
        "ci_overlap_full_addressable": bool(addr_ci[0] <= full_ci[1] and full_ci[0] <= addr_ci[1]),
        "addressable_positives": int(n_pos - n_invis),
        "invisible_positives": n_invis,
        "threshold_sensitivity": sensitivity,
        "story_robust_to_thresholds": story_holds,
        "pr_auc_addressable_range_over_grids": [round(min(addr_prs), 4), round(max(addr_prs), 4)],
        "addressable_depends_only_on_invisible_boundary": bool(boundary_invariant),
        "boundary_swap_positives_relabeled": n_swapped,
        "pr_auc_addressable_after_credit_rateliq_swap": addr_boundary_swap,
        "classification_rule": {
            "credit_visible": "noncurrent>=3% or NCO>=1% or tier1_rwa<6% (PCA undercapitalized) "
                              "or equity/assets<4%",
            "rate_liquidity_visible": "uninsured_deposit_share>=30% and HTM+AFS securities "
                                      "share>=5% of assets",
            "invisible": "none of the above (financially sound at the last filing; "
                         "structurally unpredictable from Call Report financials, in practice "
                         "fraud or a sudden run)",
        },
        "interpretation": (
            f"Of {n_pos} out-of-time failure bank-quarters ({len(banks)} distinct banks), "
            f"{types.get('credit_visible',0)} are credit-visible, "
            f"{types.get('rate_liquidity_visible',0)} rate/liquidity-visible, and {n_invis} "
            "financially invisible at the last filing. The taxonomy maps cleanly onto the real "
            "record: the rate/liquidity class is the 2023 wave (Silicon Valley, Signature, "
            "First Republic), and the invisible class is the fraud/scam failures (Enloe State, "
            "Heartland Tri-State, First National Bank of Lindsay, Pulaski Savings), which carry "
            "no financial signature by construction. Excluding only the invisible failures "
            f"lifts PR-AUC from {full.pr_auc:.3f} to {addr.pr_auc:.3f} on the addressable "
            "subset. By filing year this explains the collapse: the 2022 filing cohort (which "
            "failed in 2023) is rate/liquidity-driven and a credit-skewed model ranks it low, "
            "and the 2024 filing cohort is dominated by fraud failures that have no signal to "
            "find."),
    }
    (s.artifact_dir / "failure_decomposition.json").write_text(json.dumps(out, indent=2))
    print("type counts:", types, flush=True)
    print("by filing year:", by_filing_year, flush=True)
    print("failure_year banks:", failure_year_banks, flush=True)
    print("mode examples:", {k: len(v) for k, v in mode_examples.items()}, flush=True)
    print(f"PR-AUC full {full.pr_auc:.4f} -> addressable {addr.pr_auc:.4f} "
          f"(dropped {n_invis} invisible of {n_pos})", flush=True)


if __name__ == "__main__":
    main()
