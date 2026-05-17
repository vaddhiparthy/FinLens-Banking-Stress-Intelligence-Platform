# Validation

FinLens uses validation at three levels: connector readiness, data quality, and application smoke checks.

## Connector Readiness

```powershell
python .\scripts\run_local_pipeline.py --check-connectors
```

This checks whether optional source and platform connectors have enough configuration to run.

## Data Quality

Great Expectations assets live under `great_expectations/`.

Primary validation intent:

- confirm required fields;
- detect malformed source records;
- separate load-time checks from serving-layer checks;
- keep quality failures visible before dashboard use.

## Code and App Checks

```powershell
python -m ruff check .
python -m pytest -q
powershell -ExecutionPolicy Bypass -File .\scripts\smoke_test.ps1
```

The smoke script validates imports, chart construction, and demo stress-lab execution.

## No Fake Passes

Validation should fail loudly when required local data or connector settings are absent. Placeholder success is worse than an honest readiness gap.
