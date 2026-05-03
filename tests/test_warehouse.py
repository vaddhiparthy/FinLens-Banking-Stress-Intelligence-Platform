from pathlib import Path

import finlens.warehouse as warehouse
from finlens.config import get_settings


def test_stress_pulse_source_mode_is_demo_without_manifest(monkeypatch) -> None:
    monkeypatch.setenv("FINLENS_DATA_MODE", "mock")
    get_settings.cache_clear()
    monkeypatch.setattr(warehouse, "_latest_source_json", lambda source: None)

    try:
        assert warehouse.stress_pulse_source_mode() == "demo"
    finally:
        get_settings.cache_clear()


def test_stress_pulse_source_mode_is_live_for_valid_csv(tmp_path: Path, monkeypatch) -> None:
    csv_path = tmp_path / "stress_pulse.csv"
    csv_path.write_text(
        "\n".join(
            [
                "quarter,net_income,roa,nim,problem_banks,asset_yield,funding_cost,noncurrent_rate,nco_rate,afs_losses,htm_losses",
                "2025Q3,60,1.1,3.1,44,5.0,2.9,0.9,0.3,-30,-18",
                "2025Q4,67,1.2,3.2,41,5.1,3.0,0.8,0.2,-20,-12",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        warehouse,
        "_latest_source_json",
        lambda source: {"artifact_path": str(csv_path)},
    )

    assert warehouse.stress_pulse_source_mode() == "live"
