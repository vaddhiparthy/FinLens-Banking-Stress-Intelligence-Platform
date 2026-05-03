from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from finlens.state import save_state  # noqa: E402


def collect() -> dict:
    dags = [
        "dag_ingest_fdic",
        "dag_ingest_fred",
        "dag_ingest_qbp",
        "dag_ingest_nic",
        "dag_sync_control_plane",
        "dag_transform_and_quality",
    ]
    rows: list[dict] = []
    for dag_id in dags:
        completed = subprocess.run(
            ["airflow", "dags", "list-runs", "-d", dag_id, "--output", "json"],
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            rows.append(
                {
                    "DAG": dag_id,
                    "Latest run": "—",
                    "State": "Unavailable",
                    "Started": "—",
                    "Ended": completed.stderr[-300:] or completed.stdout[-300:],
                }
            )
            continue
        runs = json.loads(completed.stdout or "[]")
        latest = runs[0] if runs else {}
        rows.append(
            {
                "DAG": dag_id,
                "Latest run": latest.get("run_id", "No run recorded"),
                "State": latest.get("state", "No run recorded"),
                "Started": latest.get("start_date", "—"),
                "Ended": latest.get("end_date", "—"),
            }
        )
    payload = {"captured_at": datetime.now(UTC).isoformat(), "dag_runs": rows}
    save_state("airflow_run_report", payload)
    return payload


def main() -> None:
    print(json.dumps(collect(), indent=2))


if __name__ == "__main__":
    main()
