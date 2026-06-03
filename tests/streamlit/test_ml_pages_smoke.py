"""Headless smoke test: the new ML surfaces run without raising.

Uses Streamlit's AppTest runtime. With no trained artifact present (CI) the pages
take their graceful 'train the model' path; with artifacts (local) they exercise the
real model. Either way they must not raise. The Wiki page is excluded here because
st.page_link to other pages is unsupported under AppTest (works on a real server).
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
pytest.importorskip("streamlit")

PAGES = [
    "streamlit_app/app.py",
    "streamlit_app/pages/3_Predictive_Analytics.py",
    "streamlit_app/pages/7_AI_Engineering.py",
]


@pytest.mark.parametrize("page", PAGES)
def test_page_runs_without_exception(page: str) -> None:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(REPO / page), default_timeout=90).run()
    # AppTest.exception is an (empty-when-clean) ElementList, never None
    assert not at.exception, f"{page} raised: {list(at.exception)}"
