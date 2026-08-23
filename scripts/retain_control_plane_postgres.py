from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_SNAPSHOT_DAYS = 90
DEFAULT_TELEMETRY_DAYS = 365
DEFAULT_MAX_BATCH = 500
LOCK_NAME = "finlens-control-plane-retention-v1"
SCHEMA_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class RetentionPlan:
    snapshot_cutoff: datetime
    telemetry_cutoff: datetime
    max_batch: int


def build_plan(
    *,
    now: datetime,
    snapshot_days: int = DEFAULT_SNAPSHOT_DAYS,
    telemetry_days: int = DEFAULT_TELEMETRY_DAYS,
    max_batch: int = DEFAULT_MAX_BATCH,
) -> RetentionPlan:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if snapshot_days < 30:
        raise ValueError("snapshot retention cannot be shorter than 30 days")
    if telemetry_days < 90:
        raise ValueError("telemetry retention cannot be shorter than 90 days")
    if not 1 <= max_batch <= 500:
        raise ValueError("max_batch must be between 1 and 500")
    current = now.astimezone(UTC)
    return RetentionPlan(
        snapshot_cutoff=current - timedelta(days=snapshot_days),
        telemetry_cutoff=current - timedelta(days=telemetry_days),
        max_batch=max_batch,
    )


def validate_schema(schema: str) -> str:
    if not SCHEMA_RE.fullmatch(schema):
        raise ValueError("unsafe PostgreSQL schema name")
    return schema


def _connect():
    from finlens.config import get_settings

    settings = get_settings()
    settings.require("postgres_sync_dsn")
    import psycopg

    return psycopg.connect(settings.postgres_sync_dsn)


def _count_eligible(cur, schema: str, plan: RetentionPlan) -> dict[str, int]:
    cur.execute(
        f"""
        with newest as (
            select distinct on (snapshot_type) snapshot_id
            from {schema}.control_plane_snapshots
            order by snapshot_type, captured_at desc, snapshot_id desc
        )
        select count(*)::bigint
        from {schema}.control_plane_snapshots as snapshot
        where snapshot.captured_at < %s
          and not exists (
              select 1 from newest where newest.snapshot_id = snapshot.snapshot_id
          )
        """,
        (plan.snapshot_cutoff,),
    )
    snapshots = int(cur.fetchone()[0])
    cur.execute(
        f"""
        select count(*)::bigint
        from {schema}.telemetry_events
        where captured_at < %s
        """,
        (plan.telemetry_cutoff,),
    )
    telemetry = int(cur.fetchone()[0])
    return {"snapshots": snapshots, "telemetry": telemetry}


def _delete_snapshot_batch(cur, schema: str, plan: RetentionPlan) -> int:
    cur.execute(
        f"""
        with newest as (
            select distinct on (snapshot_type) snapshot_id
            from {schema}.control_plane_snapshots
            order by snapshot_type, captured_at desc, snapshot_id desc
        ), candidates as (
            select snapshot.snapshot_id
            from {schema}.control_plane_snapshots as snapshot
            where snapshot.captured_at < %s
              and not exists (
                  select 1 from newest where newest.snapshot_id = snapshot.snapshot_id
              )
            order by snapshot.captured_at, snapshot.snapshot_id
            limit %s
            for update of snapshot skip locked
        )
        delete from {schema}.control_plane_snapshots as target
        using candidates
        where target.snapshot_id = candidates.snapshot_id
        returning target.snapshot_id
        """,
        (plan.snapshot_cutoff, plan.max_batch),
    )
    return len(cur.fetchall())


def _delete_telemetry_batch(cur, schema: str, plan: RetentionPlan) -> int:
    cur.execute(
        f"""
        with candidates as (
            select event_id
            from {schema}.telemetry_events
            where captured_at < %s
            order by captured_at, event_id
            limit %s
            for update skip locked
        )
        delete from {schema}.telemetry_events as target
        using candidates
        where target.event_id = candidates.event_id
        returning target.event_id
        """,
        (plan.telemetry_cutoff, plan.max_batch),
    )
    return len(cur.fetchall())


def retain(*, apply: bool, plan: RetentionPlan) -> dict:
    from finlens.config import get_settings

    schema = validate_schema(get_settings().postgres_sync_schema)
    result = {
        "mode": "apply" if apply else "dry-run",
        "snapshot_cutoff": plan.snapshot_cutoff.isoformat(),
        "telemetry_cutoff": plan.telemetry_cutoff.isoformat(),
        "max_batch": plan.max_batch,
        "deleted": {"snapshots": 0, "telemetry": 0},
    }

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("set lock_timeout = '3s'")
            cur.execute("set statement_timeout = '30s'")
            cur.execute("select pg_try_advisory_lock(hashtextextended(%s, 0))", (LOCK_NAME,))
            if not cur.fetchone()[0]:
                result["status"] = "busy"
                return result

        try:
            with conn.cursor() as cur:
                result["eligible_before"] = _count_eligible(cur, schema, plan)
            conn.commit()
            if not apply:
                result["status"] = "ok"
                return result

            for label, delete_batch in (
                ("snapshots", _delete_snapshot_batch),
                ("telemetry", _delete_telemetry_batch),
            ):
                while True:
                    with conn.cursor() as cur:
                        deleted = delete_batch(cur, schema, plan)
                    conn.commit()
                    result["deleted"][label] += deleted
                    if deleted < plan.max_batch:
                        break

            with conn.cursor() as cur:
                result["eligible_after"] = _count_eligible(cur, schema, plan)
            conn.commit()
            result["status"] = "ok"
            return result
        finally:
            with conn.cursor() as cur:
                cur.execute("select pg_advisory_unlock(hashtextextended(%s, 0))", (LOCK_NAME,))
            conn.commit()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bound FinLens PostgreSQL control history.")
    parser.add_argument("--apply", action="store_true", help="Delete eligible rows.")
    parser.add_argument(
        "--as-of",
        help="Use an explicit timezone-aware ISO timestamp for a deterministic cutoff.",
    )
    parser.add_argument("--snapshot-days", type=int, default=DEFAULT_SNAPSHOT_DAYS)
    parser.add_argument("--telemetry-days", type=int, default=DEFAULT_TELEMETRY_DAYS)
    parser.add_argument("--max-batch", type=int, default=DEFAULT_MAX_BATCH)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        as_of = (
            datetime.fromisoformat(args.as_of.replace("Z", "+00:00"))
            if args.as_of
            else datetime.now(UTC)
        )
        plan = build_plan(
            now=as_of,
            snapshot_days=args.snapshot_days,
            telemetry_days=args.telemetry_days,
            max_batch=args.max_batch,
        )
        result = retain(apply=args.apply, plan=plan)
    except Exception as exc:
        print(json.dumps({"status": "error", "error": type(exc).__name__, "message": str(exc)}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("status") == "ok" else 75


if __name__ == "__main__":
    raise SystemExit(main())

