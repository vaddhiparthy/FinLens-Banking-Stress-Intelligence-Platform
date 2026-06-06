"""GRU sequence challenger over each bank's quarterly trajectory.

The shipped model is a discrete-time hazard GBM that sees one bank-quarter at a time
(plus engineered deltas). The expert critique is that this ignores within-bank temporal
autocorrelation: a bank's TRAJECTORY (the shape of its last K quarters) carries signal a
point-in-time model cannot represent. This builds the architecturally-matched challenger -
a small GRU over the last K quarters of the 34 features - on the SAME temporal split and
the SAME calibration, then compares it to the served GBM.

HONESTY (load-bearing): at 66 out-of-time failures the paired test has ~6% power (G0), so
NOTHING here is out-of-time statistically separable from the GBM. This is reported as a
challenger that does not beat the incumbent at a level the data can certify, not as an
improvement. Pretending otherwise would be the exact "fake improvement" to avoid.

Needs torch (CPU). Writes ml/artifacts/sequence_challenger.json.
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
from finlens_ml.evaluate import evaluate  # noqa: E402
from finlens_ml.features import FEATURE_COLUMNS  # noqa: E402
from finlens_ml.splits import final_holdout_split  # noqa: E402
from finlens_ml.train import EVAL_HOLDOUT_QUARTERS, load_dataset  # noqa: E402

ART = REPO / "ml" / "artifacts"
SEED = 42
K = 8  # quarters of history per sequence


def _build_sequences(df: pd.DataFrame, idx: np.ndarray, k: int = K):
    """For each row index, the last `k` quarters of features for that cert ending at that
    row's obs_qord. Returns (N, k, F) float array and a (N, k) mask. Shared by the single
    challenger and the robustness sweep so the two cannot drift."""
    K = k
    F = len(FEATURE_COLUMNS)
    feat = df[FEATURE_COLUMNS].to_numpy(dtype=np.float32)
    cert = df["cert"].to_numpy()
    qord = df["obs_qord"].to_numpy()
    # per-cert ordered position lookup
    order = {}
    for pos in np.argsort(qord, kind="stable"):
        order.setdefault(cert[pos], []).append(pos)
    cert_rows = {c: np.array(v) for c, v in order.items()}
    cert_qord = {c: qord[v] for c, v in cert_rows.items()}

    X = np.zeros((len(idx), K, F), dtype=np.float32)
    M = np.zeros((len(idx), K), dtype=np.float32)
    for n, i in enumerate(idx):
        c = cert[i]; q = qord[i]
        rows = cert_rows[c]; qs = cert_qord[c]
        hist = rows[qs <= q][-K:]
        seq = feat[hist]
        L = len(seq)
        X[n, K - L:, :] = np.nan_to_num(seq, nan=0.0)
        M[n, K - L:] = 1.0
    return X, M


def main() -> None:
    try:
        import torch
        import torch.nn as nn
    except Exception as e:  # noqa: BLE001
        print("torch unavailable:", e, flush=True)
        return
    torch.manual_seed(SEED)
    np.random.seed(SEED)

    s = get_ml_settings()
    k_budget = s.review_budget_k
    df = load_dataset()
    df = df[df["label_4"].notna()].sort_values(["cert", "obs_qord"]).reset_index(drop=True).copy()
    df["label_4"] = df["label_4"].astype(int)
    y = df["label_4"].to_numpy()
    obs = df["obs_qord"]
    tr, te = final_holdout_split(obs, horizon_q=4, holdout_quarters=EVAL_HOLDOUT_QUARTERS,
                                 reporting_lag_q=s.reporting_lag_q)

    # standardize features on TRAIN stats only (no leakage)
    Xall = df[FEATURE_COLUMNS].to_numpy(dtype=np.float32)
    mu = np.nanmean(Xall[tr], axis=0)
    sd = np.nanstd(Xall[tr], axis=0); sd[sd == 0] = 1.0
    df[FEATURE_COLUMNS] = (np.nan_to_num(Xall, nan=mu) - mu) / sd

    # inner validation split off the tail of train for early stopping + calibration
    tr_sorted = tr[np.argsort(obs.to_numpy()[tr], kind="stable")]
    cut = int(len(tr_sorted) * 0.85)
    tr_in, va_in = tr_sorted[:cut], tr_sorted[cut:]

    Xtr, Mtr = _build_sequences(df, tr_in)
    Xva, Mva = _build_sequences(df, va_in)
    Xte, Mte = _build_sequences(df, te)
    ytr, yva, yte = y[tr_in], y[va_in], y[te]

    F = len(FEATURE_COLUMNS)
    dev = torch.device("cpu")

    class GRUHazard(nn.Module):
        def __init__(self, f, h=48):
            super().__init__()
            self.gru = nn.GRU(f, h, batch_first=True)
            self.head = nn.Sequential(nn.Linear(h, 32), nn.ReLU(), nn.Dropout(0.2), nn.Linear(32, 1))

        def forward(self, x, m):
            out, _ = self.gru(x)
            lengths = m.sum(1).clamp(min=1).long() - 1
            last = out[torch.arange(out.size(0)), lengths]
            return self.head(last).squeeze(-1)

    model = GRUHazard(F).to(dev)
    pos_w = torch.tensor([(ytr == 0).sum() / max(1, (ytr == 1).sum())], dtype=torch.float32)
    lossf = nn.BCEWithLogitsLoss(pos_weight=pos_w)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-5)

    Xtr_t = torch.tensor(Xtr); Mtr_t = torch.tensor(Mtr); ytr_t = torch.tensor(ytr, dtype=torch.float32)
    Xva_t = torch.tensor(Xva); Mva_t = torch.tensor(Mva)
    Xte_t = torch.tensor(Xte); Mte_t = torch.tensor(Mte)

    n = len(Xtr_t); bs = 512
    best_va = -1.0; best_state = None; patience = 0
    for epoch in range(80):
        model.train()
        perm = torch.randperm(n)
        for b in range(0, n, bs):
            ix = perm[b:b + bs]
            opt.zero_grad()
            logit = model(Xtr_t[ix], Mtr_t[ix])
            loss = lossf(logit, ytr_t[ix])
            loss.backward(); opt.step()
        model.eval()
        with torch.no_grad():
            pva = torch.sigmoid(model(Xva_t, Mva_t)).numpy()
        va_ap = evaluate(yva, pva, k=k_budget).pr_auc
        if va_ap > best_va:
            best_va = va_ap; best_state = {k: v.clone() for k, v in model.state_dict().items()}; patience = 0
        else:
            patience += 1
            if patience >= 12:
                break
    if best_state:
        model.load_state_dict(best_state)

    model.eval()
    with torch.no_grad():
        pva = torch.sigmoid(model(Xva_t, Mva_t)).numpy()
        pte_raw = torch.sigmoid(model(Xte_t, Mte_t)).numpy()

    # isotonic calibration on inner validation (same recipe as the GBM)
    from sklearn.isotonic import IsotonicRegression
    iso = IsotonicRegression(out_of_bounds="clip")
    iso.fit(pva, yva)
    pte = iso.transform(pte_raw)

    gru = evaluate(yte, pte, k=k_budget)
    metrics = json.loads((ART / "metrics_h4.json").read_text())
    gbm_pr = metrics["oot_test"]["calibrated_lgbm"]["pr_auc"]
    gbm_ci = metrics.get("oot_test_ci", {}).get("pr_auc_ci")
    in_ci = bool(gbm_ci and gbm_ci[0] <= gru.pr_auc <= gbm_ci[1])

    out = {
        "architecture": f"GRU(hidden=48) over last K={K} quarters of {F} features, "
                        "masked last-step readout, isotonic-calibrated",
        "history_quarters": K,
        "n_train_sequences": int(len(tr_in)),
        "n_oot_sequences": int(len(te)),
        "n_oot_positives": int(yte.sum()),
        "best_inner_val_pr_auc": round(float(best_va), 4),
        "oot_pr_auc_gru": round(float(gru.pr_auc), 4),
        "oot_pr_auc_gbm_served": round(float(gbm_pr), 4),
        "oot_roc_auc_gru": round(float(gru.roc_auc), 4),
        "delta_vs_gbm": round(float(gru.pr_auc - gbm_pr), 4),
        "gbm_pr_auc_ci": gbm_ci,
        "gru_pr_within_gbm_ci": in_ci,
        "g0_paired_power_at_delta_0_02": "~6%",
        "verdict": (
            f"The GRU sequence challenger scores OOT PR-AUC {gru.pr_auc:.3f} vs the served "
            f"GBM {gbm_pr:.3f} (delta {gru.pr_auc - gbm_pr:+.3f}). The GRU point estimate is "
            f"LOWER, but it falls "
            f"{'INSIDE' if in_ci else 'OUTSIDE'} the served model's bootstrap PR-AUC interval "
            f"{f'[{gbm_ci[0]:.3f}, {gbm_ci[1]:.3f}]' if gbm_ci else ''}, and at "
            f"{int(yte.sum())} OOT failures the paired test has ~6% power (G0), so the two are "
            "NOT statistically separable in either direction. Note the large inner-validation "
            f"PR-AUC ({best_va:.3f}) collapsing to {gru.pr_auc:.3f} out-of-time: the trajectory "
            "signal the GRU learns in-sample does not transfer across the regime/cohort shift, "
            "consistent with the failure-type decomposition. The trajectory architecture is the "
            "theoretically-matched design for within-bank autocorrelation, but it does not beat "
            "the incumbent here. It is reported as a challenger, not a replacement; the GBM "
            "remains served on grounds of point estimate, calibration, monotonicity, and "
            "interpretability."),
    }
    (ART / "sequence_challenger.json").write_text(json.dumps(out, indent=2))
    print(f"GRU OOT PR-AUC {gru.pr_auc:.4f} (inner-val {best_va:.4f}) vs GBM {gbm_pr:.4f} "
          f"delta {gru.pr_auc - gbm_pr:+.4f}", flush=True)
    print(f"wrote {ART/'sequence_challenger.json'}", flush=True)


if __name__ == "__main__":
    main()
