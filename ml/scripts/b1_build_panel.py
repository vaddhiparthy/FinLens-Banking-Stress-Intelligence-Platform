"""B1 step 2: build the point-in-time training dataset from originally-filed Call
Reports, joined to the existing labels (failure dates are FDIC-sourced and independent
of the financial features). Output mirrors ml.training_dataset so train.py can run on
it unchanged, plus a side-by-side noncurrent diagnostic.

Saves data/pit/pit_training_dataset.parquet and prints a coverage summary.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
for p in (REPO, REPO / "src", REPO / "ml"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from finlens_ml.features import FEATURE_COLUMNS, build_features  # noqa: E402
from finlens_ml.ffiec_pit import build_pit_panel  # noqa: E402
from finlens_ml.train import load_dataset  # noqa: E402

OUT = REPO / "data" / "pit"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    print("parsing 73 originally-filed Call Report periods...", flush=True)
    raw = build_pit_panel()
    print(f"  raw point-in-time panel: {len(raw):,} bank-quarters, "
          f"{raw['cert'].nunique():,} banks, {raw['quarter'].min()}..{raw['quarter'].max()}",
          flush=True)

    feat = build_features(raw)

    # labels / panel scaffolding come from the existing dataset (FDIC failure dates,
    # obs ordinals, charter class) — these are not financial features and carry no
    # restatement look-ahead.
    fdic = load_dataset()
    keep = ["cert", "quarter", "repdte", "obs_qord", "fail_qord", "bank_class",
            "label_4", "label_status_4", "labelable_4",
            "label_8", "label_status_8", "labelable_8"]
    scaffold = fdic[keep].copy()

    pit = feat.merge(scaffold, on=["cert", "quarter"], how="inner", suffixes=("", "_lbl"))
    # prefer the scaffold's repdte/obs ordinals
    if "repdte_lbl" in pit:
        pit["repdte"] = pit["repdte_lbl"]
        pit = pit.drop(columns=[c for c in pit.columns if c.endswith("_lbl")])

    out_cols = (["cert", "bank_name", "quarter", "repdte", "obs_qord", "fail_qord",
                 "state", "bank_class"] + FEATURE_COLUMNS
                + ["label_4", "label_status_4", "labelable_4",
                   "label_8", "label_status_8", "labelable_8"])
    out_cols = [c for c in out_cols if c in pit.columns]
    pit = pit[out_cols]

    dest = OUT / "pit_training_dataset.parquet"
    pit.to_parquet(dest, index=False)
    print(f"\nwrote {dest}: {len(pit):,} rows, {len(out_cols)} cols", flush=True)
    lab = pit[pit["label_4"].notna()]
    print(f"labelable_4 rows: {len(lab):,}  positives: {int(lab['label_4'].sum())}", flush=True)

    # noncurrent diagnostic: does point-in-time populate the feature FDIC left ~half zero?
    fz = float((pd.to_numeric(fdic['noncurrent_to_loans'], errors='coerce') == 0).mean())
    pz = float((pd.to_numeric(pit['noncurrent_to_loans'], errors='coerce') == 0).mean())
    print(f"\nnoncurrent_to_loans == 0:  FDIC {fz:.1%}  vs  point-in-time {pz:.1%}", flush=True)
    print(f"noncurrent_to_loans median(>0):  FDIC "
          f"{pd.to_numeric(fdic['noncurrent_to_loans'],errors='coerce').replace(0,float('nan')).median():.3f}"
          f"  vs PIT "
          f"{pd.to_numeric(pit['noncurrent_to_loans'],errors='coerce').replace(0,float('nan')).median():.3f}",
          flush=True)


if __name__ == "__main__":
    main()
