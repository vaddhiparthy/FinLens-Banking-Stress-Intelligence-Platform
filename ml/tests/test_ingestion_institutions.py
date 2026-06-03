"""Unit tests for institution-level FDIC ingestion (no network)."""

from __future__ import annotations

import ast
from pathlib import Path

from ingestion.fdic_institutions import _unwrap, quarter_repdtes


def test_quarter_repdtes_spans_year_boundary() -> None:
    qs = quarter_repdtes("2008Q3", "2009Q2")
    assert qs == ["20080930", "20081231", "20090331", "20090630"]


def test_quarter_repdtes_single_quarter() -> None:
    assert quarter_repdtes("2010Q1", "2010Q1") == ["20100331"]


def test_unwrap_pulls_inner_data() -> None:
    raw = [{"data": {"CERT": 1, "ASSET": 100}, "score": 0}, {"data": {"CERT": 2}}]
    assert _unwrap(raw) == [{"CERT": 1, "ASSET": 100}, {"CERT": 2}]


def test_institution_ingestion_does_not_import_aws() -> None:
    # the institution ingestion path must also stay $0 even though the global
    # S3 mirror flag may be enabled on the VPS.
    path = Path(__file__).resolve().parents[2] / "ingestion" / "fdic_institutions.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            modules.update(a.name for a in node.names)
    assert "finlens.aws" not in modules
    assert not any(m.startswith("boto") for m in modules)
