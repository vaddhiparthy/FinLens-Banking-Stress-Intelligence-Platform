from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def run_dbt_build(target: str = "local") -> dict:
    from finlens.pipeline_runs import PipelineRunRecorder
    from finlens.state import save_state
    from finlens.warehouse import local_duckdb_path

    recorder = PipelineRunRecorder("dbt_build")
    env = os.environ.copy()
    env["FINLENS_DUCKDB_PATH"] = str(local_duckdb_path())
    command = [
        "dbt",
        "build",
        "--project-dir",
        str(REPO_ROOT / "dbt"),
        "--profiles-dir",
        str(REPO_ROOT / "dbt"),
        "--target",
        target,
    ]

    def execute() -> dict:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        return {
            "command": " ".join(command),
            "returncode": completed.returncode,
            "stdout_tail": completed.stdout[-4000:],
            "stderr_tail": completed.stderr[-4000:],
        }

    result = recorder.record(
        "dbt build",
        execute,
        detail=lambda payload: (
            "dbt build completed"
            if payload["returncode"] == 0
            else f"dbt build failed with return code {payload['returncode']}"
        ),
        metadata=lambda payload: payload,
        allow_failure=True,
    )
    status = "Success" if result and result["returncode"] == 0 else "Failed"
    payload = {
        "status": status,
        "target": target,
        "command": result["command"] if result else " ".join(command),
        "returncode": result["returncode"] if result else 1,
        "stdout_tail": result["stdout_tail"] if result else "",
        "stderr_tail": result["stderr_tail"] if result else "",
        "captured_at": datetime.now(UTC).isoformat(),
    }
    save_state("dbt_build_report", payload)
    recorder.finish(status)
    return payload


def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else "local"
    print(json.dumps(run_dbt_build(target), indent=2))


if __name__ == "__main__":
    main()
