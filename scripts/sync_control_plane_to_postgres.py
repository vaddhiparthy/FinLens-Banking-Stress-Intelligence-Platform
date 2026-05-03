from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _connect():
    from finlens.config import get_settings

    settings = get_settings()
    settings.require("postgres_sync_dsn")
    import psycopg

    return psycopg.connect(settings.postgres_sync_dsn)


def _ensure_tables(conn, schema: str) -> None:
    with conn.cursor() as cur:
        cur.execute(f"create schema if not exists {schema}")
        cur.execute(
            f"""
            create table if not exists {schema}.telemetry_events (
                event_id text primary key,
                event_type text not null,
                page_key text not null,
                surface text not null,
                session_id text not null,
                payload jsonb not null,
                captured_at timestamptz not null
            )
            """
        )
        cur.execute(
            f"""
            create table if not exists {schema}.control_plane_snapshots (
                snapshot_id bigserial primary key,
                snapshot_type text not null,
                snapshot_payload jsonb not null,
                captured_at timestamptz default now()
            )
            """
        )
    conn.commit()


def sync() -> dict:
    from finlens.config import get_settings
    from finlens.pipeline_status import pipeline_status_rows
    from finlens.state import load_state, save_state
    from finlens.telemetry import load_telemetry_events, telemetry_summary

    settings = get_settings()
    schema = settings.postgres_sync_schema
    synced_state = load_state("postgres_sync_state", default={"telemetry_event_ids": []})
    already_synced = set(synced_state.get("telemetry_event_ids", []))
    events = load_telemetry_events()
    pending_events = [event for event in events if event["event_id"] not in already_synced]

    with _connect() as conn:
        _ensure_tables(conn, schema)
        with conn.cursor() as cur:
            for event in pending_events:
                cur.execute(
                    f"""
                    insert into {schema}.telemetry_events
                    (event_id, event_type, page_key, surface, session_id, payload, captured_at)
                    values (%s, %s, %s, %s, %s, %s::jsonb, %s)
                    on conflict (event_id) do nothing
                    """,
                    (
                        event["event_id"],
                        event["event_type"],
                        event["page_key"],
                        event["surface"],
                        event["session_id"],
                        json.dumps(event.get("payload", {})),
                        event["captured_at"],
                    ),
                )
            cur.execute(
                f"""
                insert into {schema}.control_plane_snapshots (snapshot_type, snapshot_payload)
                values (%s, %s::jsonb), (%s, %s::jsonb), (%s, %s::jsonb)
                """,
                (
                    "pipeline_status",
                    json.dumps(pipeline_status_rows()),
                    "connector_report",
                    json.dumps(load_state("connector_report", default={})),
                    "telemetry_summary",
                    json.dumps(telemetry_summary()),
                ),
            )
        conn.commit()

    synced_state["telemetry_event_ids"] = sorted(
        already_synced | {e["event_id"] for e in pending_events}
    )
    save_state("postgres_sync_state", synced_state)
    return {
        "synced_events": len(pending_events),
        "schema": schema,
    }


if __name__ == "__main__":
    print(json.dumps(sync()))
