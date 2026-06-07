# Fact-check: Early Warning + Home

Date checked: 2026-06-06. Branch `machine-learning-portfolio`.

Sources of truth: `ml/artifacts/metrics_h4.json`, `ml/finlens_ml/features.py` (FEATURE_COLUMNS),
`ml/finlens_ml/config.py` (flag_threshold), `ml/finlens_ml/scenario.py` (live scoring path),
DuckDB `.duckdb/finlens.duckdb` (read-only), `streamlit_app/lib/data.py` loaders,
`finlens.pipeline_status.pipeline_status_rows`.

Live DuckDB snapshot at check time:
- `marts.fct_bank_failures` = 573 rows
- `marts.fct_stress_pulse` = 41 rows
- distinct FRED `series_id` in `marts.fct_financial_metrics` = 6
- `ml.training_dataset` = 448,661 rows, label_4=1 = 2,138, distinct certs = 8,803, max quarter = 2026Q1
- `pipeline_status_rows()` = 7

## Early Warning (`streamlit_app/pages/3_Early_Warning.py`)

| Page | Displayed item | Source of truth | Current? | Evidence / fix |
|---|---|---|---|---|
| Early Warning | "34 CAMELS-style Call Report ratios" (line 129) | `len(FEATURE_COLUMNS)` | PASS | FEATURE_COLUMNS = 34 exactly. Note: hardcoded literal, not derived from `len(...)`; will silently drift if the feature set changes. Consider `len(scenario.FEATURE_COLUMNS)`. |
| Early Warning | Review threshold "{thr*100:.0f}%" in score badge (line 73) | `config.flag_threshold` via `decision()` | PASS | Rendered live from `result["threshold"]` (default 0.10 -> "10%"). Fully dynamic. |
| Early Warning | Risk tier HIGH/ELEVATED/LOW thresholds (lines 53-58) | `_tier()` uses live `threshold` and `threshold/2` | PASS | Derived from the same live threshold. |
| Early Warning | Gauge probability + SHAP driver table (lines 67, 85-112) | live `scenario.score_features()` / `score_hypothetical()` | PASS | Computed live from the served model + SHAP per selection. No hardcoded numbers. |
| Early Warning | Live-tab PR-AUC "{_pr_txt}" e.g. "~0.30" (lines 213-223) | `metrics_h4.json oot_test.calibrated_lgbm.pr_auc` = 0.3014 | PASS | Read dynamically from JSON; formats to "~0.30". Fallback literal "~0.30" also matches. |
| Early Warning | "on 66 real failures" (line 223) | `metrics_h4.json test_positives` / `oot_test.calibrated_lgbm.n_positive` = 66 | PASS (fragile) | Matches artifact today, but HARDCODED literal next to the dynamically-read PR-AUC. If the panel/eval is rerun and OOT positives change, PR-AUC updates but "66" goes stale. Fix: read `n_positive` from the same JSON. |
| Early Warning | "base rate under 1%" (lines 122-123, 206-207, 275) | OOT base_rate 0.000555 (0.055%); full-panel label_4 mean 0.0051 (0.51%) | PASS | Both well under 1%. Accurate either way. |
| Early Warning | Bank pickers / failed-bank list / live directory | `scenario.bank_directory()`, `held_out_failed_banks()`, `live_bank_directory()` | PASS | All query `ml.training_dataset` live; counts/labels reflect current data (max quarter 2026Q1). |
| Early Warning | "monotone-constrained gradient-boosted hazard model" (line 132) | `MONOTONE_CONSTRAINTS` in features.py | PASS | Constraints defined and enforced; what-if caption (lines 264-267) matches signs (capital -1, noncurrent +1). |
| Early Warning | status_ribbon "Historical backtest + experimental live scoring" (line 115) | page tabs (3 backtest-style + 1 live + what-if) | PASS | Matches the surface. |

## Home (`streamlit_app/app.py`)

| Page | Displayed item | Source of truth | Current? | Evidence / fix |
|---|---|---|---|---|
| Home | metric_card "FDIC failures" = `len(failures)` (line 217) | `load_failures()` -> marts.fct_bank_failures = 573 | PASS | Live. |
| Home | metric_card "Stress periods" = `len(stress)` (line 219) | marts.fct_stress_pulse = 41 | PASS | Live. |
| Home | metric_card "FRED series" = `n_fred` (line 221) | distinct series_id = 6 | PASS | Live. |
| Home | metric_card "Pipeline flows" = `len(pipeline_rows)` (line 223) | pipeline_status_rows() = 7 | PASS | Live. |
| Home | `_data_summary()` "{len(failures):,} FDIC failure records" (line 40) | 573 | PASS | Live. |
| Home | `_data_summary()` "{len(stress):,} aggregate reporting periods" (line 48) | 41 | PASS | Live. |
| Home | `_data_summary()` "{series_count:,} FRED series" (line 54) | 6 | PASS | Live. |
| Home | `_data_summary()` "{len(pipeline_status_rows())} live pipeline movements" (line 61) | 7 | PASS | Live. Calls pipeline_status_rows() a 2nd time (minor: recompute, not a correctness issue). |
| Home | `_surface_summary()` AI surface text "out-of-time metrics, SHAP, drift, decisions, governance, and a live predictive scenario tab" (lines 90-96) | page structure | PASS | Descriptive, matches AI surface sections. |
| Home | Hero copy + "What I am working with" / "How I organised it" headings | static descriptive | PASS (copy flag below) | No factual numbers; see first-person note. |
| Home | Legal disclaimer dialog (lines 129-141) | static | PASS | No factual claims. |

## Shared shell (`streamlit_app/lib/page_shell.py`)

| Page | Displayed item | Source of truth | Current? | Evidence / fix |
|---|---|---|---|---|
| Shell | Sidebar clock date/time (lines 109-118) | `datetime.now(ZoneInfo("America/New_York"))` | PASS | Live, refreshes every 1s. |
| Shell | Footer "Public FDIC & FRED data · open-source stack" (lines 199-207) | data sources | PASS | Accurate. |
| Shell | `_META_DESCRIPTIONS` home/business/AI (lines 329-339) | model + pipeline description | PASS | Descriptive (mentions "cited RAG analyst assistant", "discrete-time hazard model", "dbt + Great Expectations"); architectural claims, no stale numbers. |
| Shell | page_intro / status_ribbon / top_navigation | render passed-in args | PASS | No embedded factual literals. |

## ui_components.py

No factual claims; pure presentation helpers (metric_card, styled_table, chart_note, etc.). PASS.

## First-person / informal wording (flag for separate copy pass)

- `app.py` line 162: eyebrow "Surya Vaddhiparthy · M.S. Data Science".
- `app.py` lines 164-168: hero "I built FinLens to turn free public banking data ... and to show the full ... build behind it."
- `app.py` line 214: heading "What I am working with".
- `app.py` line 225: heading "How I organised it".
- `app.py` lines 228-234: "I split FinLens into three views ..."
- `app.py` lines 245-247: use notice "This is my personal analytical project ..."
- (Early Warning page uses no first-person 'I/my'.)

## Hardcoded literals that should be dynamic (priority)

1. `3_Early_Warning.py` line 223 "on 66 real failures" — hardcode; PR-AUC right beside it is read from JSON. Read `n_positive` from `metrics_h4.json` to keep them in lockstep.
2. `3_Early_Warning.py` line 129 "34 CAMELS-style Call Report ratios" — hardcode; matches `len(FEATURE_COLUMNS)` today. Derive from `len(...)`.
