from finlens.telemetry import append_telemetry_event, telemetry_summary


def test_append_telemetry_event_and_summary() -> None:
    event = append_telemetry_event(
        event_type="page_view",
        page_key="stress_pulse",
        surface="business",
        session_id="unit-session",
    )

    assert event["event_type"] == "page_view"
    summary = telemetry_summary()
    assert summary["event_count"] >= 1
    assert summary["page_views"] >= 1
