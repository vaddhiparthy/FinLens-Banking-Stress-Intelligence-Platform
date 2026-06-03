"""$0 invariant, enforced by construction.

Fails the build if anything under ``ml/finlens_ml`` imports a billable/cloud
module (``finlens.aws``, ``boto3``, ``snowflake``). This turns the architecture's
"no money-touching" rule from a prose promise into a CI-enforced control: a future
commit that adds an S3 PUT or Snowflake call to the ML subsystem cannot merge.
"""

from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_PREFIXES = ("finlens.aws", "boto3", "boto", "snowflake")

ML_PACKAGE = Path(__file__).resolve().parents[1] / "finlens_ml"


def _python_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.py"))


def _imported_modules(tree: ast.AST) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.add(node.module)
    return modules


def _is_forbidden(module: str) -> bool:
    return any(module == p or module.startswith(p + ".") for p in FORBIDDEN_PREFIXES)


def test_ml_package_has_no_billable_imports() -> None:
    offenders: list[str] = []
    for path in _python_files(ML_PACKAGE):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for module in _imported_modules(tree):
            if _is_forbidden(module):
                offenders.append(f"{path.name}: imports '{module}'")
    assert not offenders, (
        "ML subsystem must touch no billable/cloud service ($0 invariant). "
        "Forbidden imports found:\n  " + "\n  ".join(offenders)
    )


def test_ml_settings_expose_no_aws_fields() -> None:
    from finlens_ml.config import get_ml_settings

    settings = get_ml_settings()
    field_names = {f.lower() for f in vars(settings)}
    banned = {"aws", "s3", "secret", "snowflake", "bucket", "credential", "mirror"}
    leaked = {f for f in field_names if any(b in f for b in banned)}
    assert not leaked, f"ML settings must expose no billable/credential fields, found: {leaked}"
