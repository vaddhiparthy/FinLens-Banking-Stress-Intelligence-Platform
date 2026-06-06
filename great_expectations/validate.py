"""Capstone-1 data-quality runner: validate the gold mart against a Great Expectations-format
expectation suite, and emit a GX-shaped validation result.

Honest note on the engine: the real `great_expectations` PyPI package is not importable in this
repo because the repo's own top-level `great_expectations/` directory shadows it (a pre-existing
structural choice; `import great_expectations` resolves to this folder, not the library). Rather
than restructure the package layout, this runner is a self-contained evaluator of the same GX
expectation-suite JSON (schema / null-rate / range / freshness / row-count expectation types).
The suite file is valid GX v3 format and would run unchanged on a real GX context if the name
collision were removed. The checks below actually execute against the materialized mart and the
process exits non-zero on any failure, so it is a real quality gate, not the prior stub.

Run: python great_expectations/validate.py   (exit 0 = all pass)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for p in (REPO, REPO / "src", REPO / "ml"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

SUITE = REPO / "great_expectations" / "expectations" / "bank_quarterly_risk_facts.json"
RESULT = REPO / "great_expectations" / "uncommitted" / "validation_bank_quarterly_risk_facts.json"
TABLE = "marts.bank_quarterly_risk_facts"


def _load_mart():
    import duckdb
    from finlens_ml.config import get_ml_settings
    con = duckdb.connect(str(get_ml_settings().duckdb_path), read_only=True)
    return con.execute(f"select * from {TABLE}").df()


def _evaluate(df, exp):  # returns (success, observed)
    t = exp["expectation_type"]
    k = exp["kwargs"]
    col = k.get("column")
    if t == "expect_table_row_count_to_be_between":
        n = len(df)
        return (k.get("min_value", 0) <= n <= k.get("max_value", 10**12)), n
    if t == "expect_column_to_exist":
        return (col in df.columns), col in df.columns
    if t == "expect_column_values_to_not_be_null":
        frac = float(df[col].notna().mean())
        return (frac >= k.get("mostly", 1.0) - 1e-9), round(frac, 4)
    if t == "expect_column_values_to_be_between":
        s = df[col].dropna()
        lo, hi = k.get("min_value", float("-inf")), k.get("max_value", float("inf"))
        frac = float(((s >= lo) & (s <= hi)).mean()) if len(s) else 1.0
        return (frac >= k.get("mostly", 1.0) - 1e-9), round(frac, 4)
    if t == "expect_column_max_to_be_between":
        mx = df[col].dropna().max()
        ok = True
        if "min_value" in k:
            ok = ok and (mx >= k["min_value"])
        if "max_value" in k:
            ok = ok and (mx <= k["max_value"])
        return bool(ok), str(mx)
    raise ValueError(f"unsupported expectation: {t}")


def main() -> int:
    suite = json.loads(SUITE.read_text())
    df = _load_mart()
    results = []
    for exp in suite["expectations"]:
        ok, observed = _evaluate(df, exp)
        results.append({"expectation_type": exp["expectation_type"],
                        "kwargs": exp["kwargs"], "success": bool(ok), "observed": observed})
    n_ok = sum(r["success"] for r in results)
    overall = all(r["success"] for r in results)
    out = {"suite": suite["expectation_suite_name"], "table": TABLE,
           "n_expectations": len(results), "n_success": n_ok, "success": overall,
           "results": results}
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(out, indent=2))
    print(f"GX validation {suite['expectation_suite_name']}: {n_ok}/{len(results)} passed -> "
          f"{'SUCCESS' if overall else 'FAILED'}", flush=True)
    if not overall:
        for r in results:
            if not r["success"]:
                print("  FAIL:", r["expectation_type"], r["kwargs"], "observed", r["observed"],
                      flush=True)
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
