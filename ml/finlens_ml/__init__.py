"""FinLens Machine Learning Engineering subsystem.

A bank financial-distress early-warning model built on per-institution FDIC Call
Report data. Discrete-time hazard framing, rolling-origin out-of-time validation,
calibrated + monotonic gradient-boosted trees, SHAP explainability, MLflow tracking,
Evidently monitoring, SR 26-2-aligned governance.

Hard invariant: nothing in this package may import ``finlens.aws``, ``boto3`` or
``snowflake``. The package exposes no AWS/billable configuration. This keeps the
subsystem at $0 cost by construction; a CI import-guard enforces it.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
