"""B1 noncurrent-field audit (reproducible generator for the blocks cited in
docs/ml/B1_POINT_IN_TIME.md). Writes two keys into ml/artifacts/b1_compare.json:

  noncurrent_field_audit:
    p9lnls_zero_rate  - FDIC P9LNLS (90+-days-past-due-AND-still-accruing only)
    nclns_zero_rate   - FDIC NCLNLS (total noncurrent = nonaccrual + 90+)
    (the gap is the evidence the shipped feature used the wrong field)

  noncurrent_reconstruction:
    category_sum_vs_official_corr / median ratio - validates the pre-2014 RC-N
    label-based category sum against the 2014+ official total (1403 + 1407) where
    both exist, justifying the point-in-time noncurrent reconstruction.

No hand-entered numbers: every value is computed here from the committed panel +
the FFIEC bulk zips. Run after build_dataset.py and b1_compare.py.
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
for p in (REPO, REPO / "src", REPO / "ml"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from finlens_ml.config import get_ml_settings  # noqa: E402
from finlens_ml.ffiec_pit import RAW, _is_noncurrent_label, _LABELS, _num, _read  # noqa: E402

ART = REPO / "ml" / "artifacts"


def _category_sum(rcn: pd.DataFrame) -> pd.Series:
    """Pre-2014 label-based per-category noncurrent sum (one filer-domain per item)."""
    by_item: dict[str, str] = {}
    for c in rcn.columns:
        if not _is_noncurrent_label(_LABELS.get(str(c).upper(), "")):
            continue
        item = str(c)[-4:]
        cur = by_item.get(item)
        if cur is None or (str(c).upper().startswith("RCFD") and not cur.upper().startswith("RCFD")):
            by_item[item] = c
    tot = pd.Series(0.0, index=rcn.index)
    anyv = pd.Series(False, index=rcn.index)
    for col in by_item.values():
        v = pd.to_numeric(rcn[col].astype(str).str.replace(",", "", regex=False), errors="coerce")
        tot = tot.add(v, fill_value=0)
        anyv = anyv | v.notna()
    return tot.where(anyv)


def main() -> None:
    import duckdb

    con = duckdb.connect(str(get_ml_settings().duckdb_path), read_only=True)
    p9 = con.execute(
        "select avg(case when P9LNLS=0 then 1.0 else 0 end) from ml.training_dataset"
    ).fetchone()[0]
    nc = con.execute(
        "select avg(case when NCLNLS=0 then 1.0 else 0 end) from ml.training_dataset"
    ).fetchone()[0]
    con.close()

    # reconstruction validation: 2018Q1 has BOTH the official total and the categories
    with zipfile.ZipFile(RAW / "call_20180331.zip") as zf:
        rcn = _read(zf, "Schedule RCN").set_index("IDRSSD")
    official = _num(rcn, "RCFD1403", "RCON1403").add(
        _num(rcn, "RCFD1407", "RCON1407"), fill_value=0)
    catsum = _category_sum(rcn)
    both = official.notna() & catsum.notna() & (official > 0) & (catsum > 0)

    audit = {
        "p9lnls_zero_rate": round(float(p9), 3),
        "nclns_zero_rate": round(float(nc), 3),
        "note": ("P9LNLS = 90+-days-past-due-and-still-accruing only (normal to be zero); "
                 "NCLNLS = total noncurrent (nonaccrual + 90+). FinLens originally used "
                 "P9LNLS; fixed to NCLNLS in features.py."),
    }
    recon = {
        "validation_quarter": "2018Q1",
        "category_sum_vs_official_corr": round(float(official[both].corr(catsum[both])), 3),
        "category_sum_over_official_median_ratio": round(float((catsum[both] / official[both]).median()), 3),
        "n_banks_both_nonzero": int(both.sum()),
        "note": ("pre-2014 RC-N has no total line; the label-based category sum is validated "
                 "against the 2014+ official total (1403+1407) where both exist - rank-correct "
                 "but magnitude-light, hence the 2014 boundary level shift."),
    }

    dest = ART / "b1_compare.json"
    cmp = json.loads(dest.read_text()) if dest.exists() else {}
    cmp["noncurrent_field_audit"] = audit
    cmp["noncurrent_reconstruction"] = recon
    dest.write_text(json.dumps(cmp, indent=2))
    print("noncurrent_field_audit:", audit)
    print("noncurrent_reconstruction:", recon)
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
