from __future__ import annotations

from uuid import uuid4

import streamlit as st

from finlens.telemetry import append_telemetry_event


def record_page_view(page_key: str, surface: str) -> None:
    if "telemetry_session_id" not in st.session_state:
        st.session_state["telemetry_session_id"] = str(uuid4())
    marker = f"telemetry_page_view_{page_key}"
    if st.session_state.get(marker):
        return
    # Telemetry is observability, not a feature the user sees. A failed write
    # (e.g. a transient Windows file lock on the state file) must never surface a
    # traceback or blank the page, so swallow anything that goes wrong here.
    try:
        append_telemetry_event(
            event_type="page_view",
            page_key=page_key,
            surface=surface,
            session_id=st.session_state["telemetry_session_id"],
        )
    except Exception:  # noqa: BLE001 - telemetry must never break a page render
        return
    st.session_state[marker] = True
