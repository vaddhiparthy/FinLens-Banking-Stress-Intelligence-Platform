"""Export panel facts (row/bank counts, quarter range, OOT window/failure count) to a single
committed artifact so the UI never hardcodes these drift-prone numbers. Regenerate after a panel
rebuild or retrain:  python ml/scripts/export_panel_facts.py

Reads DuckDB ml.training_dataset (the live panel) + ml/artifacts/metrics_h4.json (the OOT facts)
and writes ml/artifacts/panel_facts.json. Deploy-safe: the UI reads the committed JSON, not the DB.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
for p in (REPO, REPO / "src", REPO / "ml"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

ART = REPO / "ml" / "artifacts"


def main() -> None:
    import duckdb

    from finlens_ml.config import get_ml_settings

    con = duckdb.connect(str(get_ml_settings().duckdb_path), read_only=True)
    n_rows, n_banks, qmin, qmax = con.execute(
        "select count(*), count(distinct cert), min(quarter), max(quarter) "
        "from ml.training_dataset"
    ).fetchone()

    metrics = json.loads((ART / "metrics_h4.json").read_text())
    npos = metrics.get("test_positives") or (
        metrics.get("oot_test", {}).get("calibrated_lgbm", {}).get("n_positive")
    )
    facts = {
        "n_panel_rows": int(n_rows),
        "n_banks": int(n_banks),
        "min_quarter": qmin,
        "max_quarter": qmax,
        "oot_window_quarters": int(metrics.get("eval_window_quarters"))
        if metrics.get("eval_window_quarters")
        else None,
        "oot_failures": int(npos) if npos else None,
        "source": "generated from DuckDB ml.training_dataset + metrics_h4.json",
    }
    (ART / "panel_facts.json").write_text(json.dumps(facts, indent=2))
    print("wrote", ART / "panel_facts.json", facts)


if __name__ == "__main__":
    main()
