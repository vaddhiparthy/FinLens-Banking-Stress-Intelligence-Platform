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
    append_telemetry_event(
        event_type="page_view",
        page_key=page_key,
        surface=surface,
        session_id=st.session_state["telemetry_session_id"],
    )
    st.session_state[marker] = True
