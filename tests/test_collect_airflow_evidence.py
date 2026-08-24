from datetime import UTC, datetime
from unittest import TestCase, main, mock

from scripts import collect_airflow_evidence


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.query = None
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute(self, query, params):
        self.query = query
        self.params = params

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, rows):
        self.fake_cursor = FakeCursor(rows)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def cursor(self):
        return self.fake_cursor


class CollectAirflowEvidenceTests(TestCase):
    def test_collect_reads_metadata_without_airflow_cli(self) -> None:
        started = datetime(2026, 8, 24, 4, tzinfo=UTC)
        ended = datetime(2026, 8, 24, 4, 1, tzinfo=UTC)
        connection = FakeConnection(
            [("dag_transform_and_quality", "scheduled__current", "success", started, ended)]
        )
        calls = []

        def connect(dsn, **kwargs):
            calls.append((dsn, kwargs))
            return connection

        saved = {}
        with mock.patch.object(
            collect_airflow_evidence,
            "save_state",
            lambda name, payload: saved.update(name=name, payload=payload),
        ):
            payload = collect_airflow_evidence.collect(
                "postgresql://metadata", connect=connect
            )

        self.assertEqual(
            calls,
            [
                (
                    "postgresql://metadata",
                    {"options": "-c default_transaction_read_only=on"},
                )
            ],
        )
        self.assertIn("distinct on (dag_id)", connection.fake_cursor.query.lower())
        self.assertEqual(len(connection.fake_cursor.params[0]), 7)
        by_dag = {row["DAG"]: row for row in payload["dag_runs"]}
        self.assertEqual(
            by_dag["dag_transform_and_quality"],
            {
                "DAG": "dag_transform_and_quality",
                "Latest run": "scheduled__current",
                "State": "success",
                "Started": started.isoformat(),
                "Ended": ended.isoformat(),
            },
        )
        self.assertEqual(by_dag["dag_ingest_qbp"]["State"], "No run recorded")
        self.assertEqual(saved["name"], "airflow_run_report")

    def test_collect_requires_dedicated_read_only_dsn(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "AIRFLOW_METADATA_DSN is required"):
                collect_airflow_evidence.collect()


if __name__ == "__main__":
    main()
