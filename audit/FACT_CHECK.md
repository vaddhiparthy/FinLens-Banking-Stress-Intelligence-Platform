# FinLens fact-check & currency checklist (durable)

Purpose: confirm that every value, metric, claim, and date shown anywhere on the website
reflects the CURRENT state of the data and the model, with no stale, hardcoded-drifting, or
fabricated figures. This is a standing document: re-run the protocol at the bottom after ANY
change and before any sign-off.

Status legend: PASS = verified against source-of-truth and current. FIXED = was stale/wrong,
corrected this pass (see note). LIVE = computed at render time from DuckDB/artifacts (cannot
drift). DOC = descriptive copy, no figure to drift.

Per-surface detail (the raw fact-check sweep) lives in `audit/factcheck/*.md`. This file is the
consolidated, post-remediation status.

## Source-of-truth map
| Domain | Source of truth |
|---|---|
| Panel counts, quarter range, OOT failures | `ml/artifacts/panel_facts.json` (regenerate: `python ml/scripts/export_panel_facts.py`) |
| Served model metrics (PR-AUC, ROC, recall, ECE) | `ml/artifacts/metrics_h4.json`, `viz_pack.json` |
| Robustness analyses | `ml/artifacts/{failure_decomposition,pooled_vs_addressable,cblr_robustness,competing_risks,fine_gray,b1_compare,calibration_bakeoff,sequence_challenger,maxout_experiment}.json` |
| Data quality gate | `great_expectations/validation_result.json` (regenerate: `python great_expectations/validate.py`) |
| dbt build | `dbt/target/run_results.json` (live) → `dbt_artifact_summary()` |
| Pipeline/connector/platform state | `data/state/*.json` (refresh: `python scripts/run_local_pipeline.py --probe-platform --run-dbt-build --allow-missing-connectors`) |
| Business surface figures | DuckDB marts, queried live at render |
| RAG metrics | `rag/eval_report.json` |
| Failure causes + citations | `ml/finlens_ml/failure_cause_labels.py` |

## Home (`app.py`)
| Item | Source | Status | Note |
|---|---|---|---|
| FDIC failures / stress periods / FRED series / pipeline flows counts | DuckDB + loaders | LIVE | computed at render |
| Hero + section copy | — | FIXED | first-person voice removed ("FinLens turns…", "What it is built on", "How it is organised", use-notice) |
| Disclaimer gate copy | — | PASS | already third-person |

## Business — Stress Pulse / Failure Forensics / Macro Transmission
| Item | Source | Status | Note |
|---|---|---|---|
| All cards (net income, ROA, NIM, failure counts, macro series, latest dates) | DuckDB marts, live | LIVE | 23 items verified against the live DB |
| Stress Pulse ROA source caption | `stress_pulse_source_mode()` | FIXED | source mode now `live` after pipeline refresh; caption attributes correctly |
| `render_public_data_stress_snapshot` (hardcoded 2010 / "March 2023") | — | PASS (dead) | unreachable empty-state branch; flagged for removal in UI pass |

## Early Warning (`3_Early_Warning.py`)
| Item | Source | Status | Note |
|---|---|---|---|
| Live bank score, threshold, tiers, gauge, SHAP table | `scenario.py` + served model | LIVE | scored at render |
| "N CAMELS ratios" | `len(FEATURE_COLUMNS)` | FIXED | was hardcoded "34" |
| "N real failures" | `panel_facts.json` | FIXED | was hardcoded "66" |
| Served PR-AUC text | `metrics_h4.json` | LIVE | read at render |

## Data Engineering (`4_Data_Engineering.py`)
| Item | Source | Status | Note |
|---|---|---|---|
| dbt Data Quality Summary (11 models / 7 tests / 0 fail) | `dbt/target/run_results.json` | FIXED | double-count bug removed; counts now read only from live run_results; captured today |
| Pipeline status, connector, platform, latest run | `data/state/*.json` | FIXED | refreshed via local pipeline to current date; Snowflake honestly shows Failed (free trial ended); Postgres honestly Deferred |
| Reconciliation table | `stress_pulse_source_mode()` | FIXED | now `live`; no longer contradicts the pipeline table |
| Great Expectations result (20/20) | `great_expectations/validation_result.json` | LIVE/FIXED | re-run 20/20, committed snapshot regenerated |
| Warehouse inventory layers | `evidence.warehouse_table_rows()` | FIXED | per-schema medallion mapping; views included |
| dbt SQL excerpt model ref | — | FIXED | `stg_fdic_failures` → `stg_fdic_failed_banks` |
| Empty-state cell placeholders | — | FIXED | mangled `", "` → em-dash |
| Service endpoints + deploy artifacts | `serve.py`/`api/routers/*`/`deploy/k8s/*` | PASS | match real routes/files |
| Deploy fallback (state files gitignored) | — | PASS | renders honest Pending/Scaffolded/Deferred, not fake live |

## AI Engineering (`7_AI_Engineering.py`)
| Item | Source | Status | Note |
|---|---|---|---|
| Pipeline flow tiles (448,661 / ~8,800 / 2008Q1–2026Q1 / 28-q) | `panel_facts.json` | FIXED | were hardcoded; now loaded |
| Model Quality hero + curves + CIs | `metrics_h4.json`, `viz_pack.json` | LIVE | loaded |
| Decomposition / challenger "66" | `panel_facts.oot_failures` | FIXED | were hardcoded in headings/captions |
| Robustness cross-checks (calibration, CBLR, competing-risks, B1, maxout) | their artifacts | LIVE | loaded via ml_charts loaders |
| Maxout "served 0.294" vs headline 0.301 | — | FIXED | clarified wording (ladder = quick single-run; champion = same bagged design) |
| Notebook intro copy | — | FIXED | first-person removed |

## Wiki (`6_Wiki.py` + content)
| Item | Source | Status | Note |
|---|---|---|---|
| All 42 article bodies | — | FIXED | rewritten to formal third-person; 0 first-person; all numbers/facts preserved (verified body length 100%, same keys) |
| Navigation tree | `wiki_structure.py` | FIXED | 0 orphaned/unreachable articles, 0 blank entries; superseded drafts excluded |
| Corpus stats (articles/sections/words) | computed | LIVE | derived from corpus |

## Floating assistant (chat widget)
| Item | Source | Status | Note |
|---|---|---|---|
| Cached example answers | `rag/demo_answers.json` | FIXED | corrected the inaccurate "addressable 0.382 for every family" answer to the accurate pooled-vs-addressable + cross-family-lift statement |
| Live answers | local RAG (`rag/graph.py`) | PASS | retrieval prioritises the named bank; only cited sources listed |
| Rate limit | session_state | PASS | 10 live questions/session |

## Bank Report (`8_Bank_Report.py`)
| Item | Source | Status | Note |
|---|---|---|---|
| Distress probability, threshold, flag, outcome | `scenario.score_features` (live model) | LIVE | scored at render for the selected CERT |
| SHAP drivers | `scenario` reasons | LIVE | per-bank, at render |
| Ratios vs peer medians | `scenario.baseline_features()` | LIVE | panel medians at render |
| Regulator cause + citation (failures) | `failure_cause_labels.py` | LIVE | per-bank lookup |

## Fixes applied this pass (summary)
1. dbt summary double-count → counts read only from live `run_results.json`.
2. Operational snapshots refreshed to current date (Snowflake/Postgres failures shown honestly).
3. De-hardcoded panel counts / quarter range / OOT failures / feature count across AI + Early
   Warning via `panel_facts.json`.
4. Warehouse layer mislabel, dead SQL ref, mangled placeholders fixed.
5. Wiki rewritten to formal third-person; orphan articles placed; superseded drafts excluded.
6. Home + AI first-person voice removed (site-wide first-person voice = 0).
7. Inaccurate cached RAG answer corrected; RAG retrieval/citation precision fixed.
8. GX snapshot regenerated (20/20); gold mart confirmed unchanged at 448,661.

## Re-verification protocol (run after any change)
```
# 1. panel facts current
python ml/scripts/export_panel_facts.py

# 2. data-quality gate
python great_expectations/validate.py            # expect 20/20

# 3. DuckDB truth spot-checks
python -c "import duckdb;c=duckdb.connect('.duckdb/finlens.duckdb',read_only=True);print(c.execute('select count(*),count(distinct cert),min(quarter),max(quarter) from ml.training_dataset').fetchone())"

# 4. tests
python -m pytest tests/ ml/tests/ -q             # expect 82 passed

# 5. UI no first-person voice (expect 0, ignoring %I time-format and the 'I understand' button)
grep -rnoE "\b(I|I'm|I've|my)\b" streamlit_app --include=*.py | grep -vE "%I|I understand|#"

# 6. E2E surfaces + widget + report
cd audit/e2e && npx playwright test --config playwright.config.mjs
```
