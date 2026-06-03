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
