"""Rare-event evaluation metrics — the ones that actually matter here.

For a <1% base-rate distress model, accuracy and ROC-AUC are misleading. The headline
metrics are PR-AUC (average precision), recall@k at a supervisory review budget, and
Brier score / calibration. ROC-AUC is reported only for comparability with the
literature. No billable imports ($0 invariant).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score


@dataclass(frozen=True)
class EvalMetrics:
    n: int
    n_positive: int
    base_rate: float
    pr_auc: float          # average precision — PRIMARY
    roc_auc: float         # comparability only
    brier: float           # calibration quality
    recall_at_k: float     # recall within the review budget k
    precision_at_k: float
    k: int

    def as_dict(self) -> dict:
        return asdict(self)


def recall_precision_at_k(y_true: np.ndarray, y_score: np.ndarray, k: int) -> tuple[float, float]:
    """Of the top-k highest-scored banks, what fraction of true positives are caught
    (recall@k) and what fraction of the flagged are real (precision@k)."""
    k = min(k, len(y_score))
    if k == 0:
        return 0.0, 0.0
    order = np.argsort(-y_score)[:k]
    flagged = y_true[order]
    total_pos = int(y_true.sum())
    recall = float(flagged.sum() / total_pos) if total_pos > 0 else float("nan")
    precision = float(flagged.sum() / k)
    return recall, precision


def evaluate(y_true: np.ndarray, y_score: np.ndarray, k: int = 200) -> EvalMetrics:
    y_true = np.asarray(y_true).astype(int)
    y_score = np.asarray(y_score, dtype=float)
    n_pos = int(y_true.sum())
    n = len(y_true)
    # PR-AUC / ROC-AUC / Brier require both classes present
    if n_pos == 0 or n_pos == n:
        pr = roc = float("nan")
    else:
        pr = float(average_precision_score(y_true, y_score))
        roc = float(roc_auc_score(y_true, y_score))
    brier = float(brier_score_loss(y_true, y_score)) if n > 0 else float("nan")
    recall_k, precision_k = recall_precision_at_k(y_true, y_score, k)
    return EvalMetrics(
        n=n,
        n_positive=n_pos,
        base_rate=float(n_pos / n) if n else float("nan"),
        pr_auc=pr,
        roc_auc=roc,
        brier=brier,
        recall_at_k=recall_k,
        precision_at_k=precision_k,
        k=k,
    )


def bootstrap_metrics(
    y_true: np.ndarray, y_score: np.ndarray, k: int = 200, n_boot: int = 2000, seed: int = 42
) -> dict:
    """Stratified bootstrap 95% CIs. With ~66 positives a point estimate is not a
    defensible result, so PR-AUC / ROC-AUC / recall@k are reported with intervals."""
    y_true = np.asarray(y_true).astype(int)
    y_score = np.asarray(y_score, dtype=float)
    n = len(y_true)
    rng = np.random.default_rng(seed)
    aps: list[float] = []
    rocs: list[float] = []
    recs: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        yt, ys = y_true[idx], y_score[idx]
        if yt.sum() == 0 or yt.sum() == len(yt):
            continue
        aps.append(float(average_precision_score(yt, ys)))
        rocs.append(float(roc_auc_score(yt, ys)))
        recs.append(recall_precision_at_k(yt, ys, k)[0])

    def _ci(a: list[float]) -> list[float]:
        arr = np.asarray(a, dtype=float)
        if arr.size == 0:
            return [float("nan"), float("nan")]
        return [float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5))]

    return {
        "n_boot_effective": len(aps),
        "pr_auc_ci": _ci(aps),
        "roc_auc_ci": _ci(rocs),
        "recall_at_k_ci": _ci(recs),
    }


def paired_bootstrap_ap_diff(
    y_true: np.ndarray, score_a: np.ndarray, score_b: np.ndarray,
    n_boot: int = 2000, seed: int = 42,
) -> dict:
    """Paired bootstrap of (AP_a - AP_b): is model A's PR-AUC edge over benchmark B
    real, or inside the noise band? Reports the CI of the difference and P(A>B)."""
    y_true = np.asarray(y_true).astype(int)
    a = np.asarray(score_a, dtype=float)
    b = np.asarray(score_b, dtype=float)
    n = len(y_true)
    rng = np.random.default_rng(seed)
    diffs: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        yt = y_true[idx]
        if yt.sum() == 0 or yt.sum() == len(yt):
            continue
        diffs.append(
            float(average_precision_score(yt, a[idx]) - average_precision_score(yt, b[idx]))
        )
    arr = np.asarray(diffs, dtype=float)
    if arr.size == 0:
        return {"ap_diff_median": float("nan"), "ap_diff_ci": [float("nan"), float("nan")],
                "prob_a_beats_b": float("nan")}
    return {
        "ap_diff_median": float(np.median(arr)),
        "ap_diff_ci": [float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5))],
        "prob_a_beats_b": float((arr > 0).mean()),
    }


def calibration_report(y_true: np.ndarray, y_score: np.ndarray, n_bins: int = 10) -> dict:
    """Honest calibration measurement for a rare-event model. The all-rows Brier is
    dominated by true negatives and nearly uninformative, so we also report ECE
    (expected calibration error), the Brier restricted to the top-scoring decile
    (where decisions are actually made), and observed-vs-predicted in that decile."""
    y_true = np.asarray(y_true).astype(int)
    y_score = np.asarray(y_score, dtype=float)
    n = len(y_true)
    if n == 0:
        return {"ece": float("nan"), "brier_overall": float("nan"),
                "brier_top_decile": float("nan"), "top_decile_obs": float("nan"),
                "top_decile_pred": float("nan")}
    brier_overall = float(brier_score_loss(y_true, y_score)) if y_true.sum() else float("nan")
    # ECE over equal-width probability bins
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    idx = np.clip(np.digitize(y_score, bins) - 1, 0, n_bins - 1)
    ece = 0.0
    for b in range(n_bins):
        m = idx == b
        if not m.any():
            continue
        conf = float(y_score[m].mean())
        acc = float(y_true[m].mean())
        ece += (m.sum() / n) * abs(acc - conf)
    # top-decile (where flags happen)
    k = max(1, n // 10)
    top = np.argsort(-y_score)[:k]
    yt, st = y_true[top], y_score[top]
    brier_top = float(np.mean((st - yt) ** 2))
    return {
        "ece": float(ece),
        "brier_overall": brier_overall,
        "brier_top_decile": brier_top,
        "top_decile_obs": float(yt.mean()),
        "top_decile_pred": float(st.mean()),
    }


def evaluate_by_cohort(
    y_true: np.ndarray, y_score: np.ndarray, cohort: np.ndarray, k: int = 50
) -> dict[str, dict]:
    """Per-cohort (e.g. per test quarter / crisis-vs-calm / size tier) metrics.
    A model that only works in crisis years is not production-ready — this exposes it."""
    out: dict[str, dict] = {}
    cohort = np.asarray(cohort)
    for c in sorted(set(cohort.tolist())):
        mask = cohort == c
        out[str(c)] = evaluate(np.asarray(y_true)[mask], np.asarray(y_score)[mask], k=k).as_dict()
    return out
