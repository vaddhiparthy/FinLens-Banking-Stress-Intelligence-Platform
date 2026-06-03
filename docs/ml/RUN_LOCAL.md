# Running the FinLens ML subsystem locally

All free, $0, runs on CPU. Verified end to end on Windows (Python 3.13 venv).

## 0. One-time setup
```powershell
# from repo root
uv sync --extra ml --group dev        # or: pip install -e ".[ml,dev]"
# evidently is a SEPARATE extra (pins plotly<6); install it isolated only for monitoring:
#   uv run --isolated --no-project --with "evidently>=0.7" --with pandas python ml/finlens_ml/monitor.py
```

## 1. Build the dataset (real FDIC data, ~2-3 min, one fetch)
```powershell
.venv\Scripts\python.exe ml\scripts\build_dataset.py --start 2008Q1
# -> ml.training_dataset in .duckdb/finlens.duckdb (448k bank-quarters, 73 quarters)
```

## 2. Train the model (real out-of-time evaluation + MLflow)
```powershell
.venv\Scripts\python.exe ml\finlens_ml\train.py --horizon 4
# -> ml/artifacts/: booster_h4.txt, calibrated_h4.skops, metrics_h4.json
# OOT (2019-2026, 66 real failures): calibrated PR-AUC 0.218 vs logit 0.108, ROC 0.875
```

## 3. Governance docs + drift (optional)
```powershell
.venv\Scripts\python.exe ml\finlens_ml\model_card.py      # MODEL_CARD.md + VALIDATION_REPORT.md
# monitor (evidently isolated to avoid the plotly clash):
.venv\Scripts\python.exe ml\finlens_ml\monitor.py         # drift_report.json (if evidently installed in this env)
```

## 4. Serve the model (FastAPI)
```powershell
$env:PYTHONPATH="src;ml;."; $env:OMP_NUM_THREADS="1"
.venv\Scripts\python.exe -m uvicorn finlens_ml.serve:app --port 8077
# GET  /health           -> {"status":"ok"}
# GET  /ready            -> {"status":"ready","model_version":"finlens-distress-h4-..."}
# POST /predict          {"features":{"tier1_rwa_ratio":3.0,"roa":-3.0}} -> prob + flag + SHAP reasons
# POST /predict/batch    {"records":[{...},{...}]}
```

## 5. Run the website (Streamlit, 3 surfaces)
```powershell
$env:PYTHONPATH="src;ml;."
.venv\Scripts\python.exe -m streamlit run streamlit_app\app.py
# Surfaces: Business / Data Engineering / AI. The AI surface mirrors the DE flow and
# shows real metrics; Business > Predictive Analytics is the live interactive model tab
# (insert a bank by CERT, hold out a real failure, hypothetical what-if).
```

## 6. Tests + gates
```powershell
.venv\Scripts\python.exe -m pytest -q              # full suite
.venv\Scripts\python.exe ml\scripts\metric_gate.py # model metric gate (CI)
```

## Notes
- $0 by construction: a CI import-guard fails the build if any ML module imports
  `finlens.aws` / `boto3` / `snowflake`. No paid APIs (FDIC/FRED are free).
- VPS deploy is intentionally deferred and not automated here; the local topology
  mirrors the VPS so deployment is a config swap (MLflow URI -> Postgres), not a rewrite.
