from pathlib import Path


def test_disclaimer_observer_uses_parent_document_realm() -> None:
    source = (Path(__file__).resolve().parents[2] / "streamlit_app" / "app.py").read_text(
        encoding="utf-8"
    )
    assert "var Observer = window.parent.MutationObserver;" in source
    assert "var root = doc.body || doc.documentElement;" in source
    assert "if (root && Observer)" in source
    assert "obs.observe(root" in source
    assert "new MutationObserver(kill)" not in source
