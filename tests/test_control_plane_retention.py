from datetime import UTC, datetime, timedelta

import pytest

from scripts.retain_control_plane_postgres import build_plan, main, validate_schema


def test_build_plan_uses_utc_cutoffs_and_bounded_batch() -> None:
    now = datetime(2026, 8, 23, 5, 0, tzinfo=UTC)
    plan = build_plan(now=now, snapshot_days=90, telemetry_days=365, max_batch=500)

    assert plan.snapshot_cutoff == now - timedelta(days=90)
    assert plan.telemetry_cutoff == now - timedelta(days=365)
    assert plan.max_batch == 500


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"snapshot_days": 29}, "snapshot retention"),
        ({"telemetry_days": 89}, "telemetry retention"),
        ({"max_batch": 0}, "max_batch"),
        ({"max_batch": 501}, "max_batch"),
    ],
)
def test_build_plan_rejects_unsafe_limits(kwargs: dict, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        build_plan(now=datetime(2026, 8, 23, tzinfo=UTC), **kwargs)


def test_build_plan_rejects_naive_time() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        build_plan(now=datetime(2026, 8, 23))


@pytest.mark.parametrize("schema", ["finlens", "control_plane_2", "_safe"])
def test_validate_schema_accepts_identifiers(schema: str) -> None:
    assert validate_schema(schema) == schema


@pytest.mark.parametrize("schema", ["", "finlens;drop schema public", "a-b", "1bad"])
def test_validate_schema_rejects_unsafe_identifiers(schema: str) -> None:
    with pytest.raises(ValueError, match="unsafe"):
        validate_schema(schema)


def test_cli_rejects_naive_as_of(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--as-of", "2026-08-23T05:00:00"]) == 1
    assert "timezone-aware" in capsys.readouterr().out

