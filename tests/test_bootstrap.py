from finlens.bootstrap import (
    SourceDefinition,
    run_active_sources,
    source_checks,
    validate_active_sources,
)
from finlens.config import Settings


def test_source_checks_flag_missing_connectors() -> None:
    settings = Settings(
        finlens_active_sources="fdic,fred,qbp,nic",
        fred_api_key=None,
        fdic_qbp_source_url=None,
        nic_current_parent_source_url=None,
    )

    checks = {check.key: check for check in source_checks(settings)}

    assert checks["fdic"].status == "ready"
    assert checks["fred"].status == "missing_connector"
    assert checks["qbp"].status == "missing_connector"
    assert checks["nic"].status == "missing_connector"


def test_validate_active_sources_raises_with_summary(monkeypatch) -> None:
    settings = Settings(finlens_active_sources="fred", fred_api_key=None)
    monkeypatch.setattr("finlens.bootstrap.save_connector_report", lambda checks: None)

    try:
        validate_active_sources(settings)
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected connector validation failure")

    assert "fred" in message
    assert "fred_api_key" in message


def test_run_active_sources_uses_selected_sources(monkeypatch) -> None:
    settings = Settings(finlens_active_sources="fdic,fred", fred_api_key="secret")
    seen: list[str] = []
    monkeypatch.setattr("finlens.bootstrap.save_connector_report", lambda checks: None)
    monkeypatch.setitem(
        run_active_sources.__globals__["SOURCE_DEFINITIONS"],
        "fdic",
        SourceDefinition(
            key="fdic",
            label="FDIC BankFind failures",
            required_env=(),
            cadence="manual",
            runner=lambda: seen.append("fdic") or {"ok": True},
        ),
    )
    monkeypatch.setitem(
        run_active_sources.__globals__["SOURCE_DEFINITIONS"],
        "fred",
        SourceDefinition(
            key="fred",
            label="FRED series batch",
            required_env=("fred_api_key",),
            cadence="daily",
            runner=lambda: seen.append("fred") or {"ok": True},
        ),
    )

    results = run_active_sources(settings, selected_sources=["fdic"])

    assert list(results) == ["fdic"]
    assert seen == ["fdic"]
