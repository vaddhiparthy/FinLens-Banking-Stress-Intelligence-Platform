# Business Surface Fact-Check

Verified 2026-06-06 against live DuckDB (`.duckdb/finlens.duckdb`, read-only) and warehouse/data source code.
Data mode = `live`. All three pages read marts tables from DuckDB; none read `load_state()` snapshots, so there are no stale-snapshot reads on these pages.

Runtime facts captured:
- `marts.fct_bank_failures`: 573 rows, years 2000-2026; latest year 2026 (1 failure: Metropolitan Capital Bank & Trust, 2026-01-30); top state GA (93); `assets_millions` all NULL; 307 distinct acquirers.
- `marts.fct_financial_metrics`: 31,205 rows. Latest per series: UNRATE 4.3 (2026-03-01), DGS10 4.34 / DGS2 3.83 (2026-04-23, 10Y-2Y=0.51), CPIAUCSL 330.293 (2026-03-01), CSUSHPINSA 326.612 (2026-01-01), GDP latest 2025-10-01.
- `marts.fct_stress_pulse`: 41 rows, last quarter 2025Q4 (net_income 294.353, roa 1.1698, nim 2.9191; problem_banks/asset_yield/funding_cost/afs_losses/htm_losses all NULL). Prior 2024Q4 net_income 267.095, nim 2.8957.
- `stress_pulse_source_mode()` returns **"pending"** (NOT "live"): the qbp manifest `artifact_path` points to a different machine path (`C:\Users\vaddh\OneDrive\Documents\Projects\Creations\Live\FinLens\...`) that does not exist here, even though the 41 stress-pulse rows are already baked into DuckDB.

| Page | Displayed item | Source of truth | Current? | Evidence / fix |
|---|---|---|---|---|
| Stress Pulse | Aggregate net income card `$294B`, `2025Q4 · QoQ +27B` (0_Stress_Pulse.py:420-424) | `fct_stress_pulse` last row | PASS | net_income 294.353→`$294B`; QoQ 294.353-267.095=+27 ✓ |
| Stress Pulse | Industry ROA value `1.17%` (0:426-431) | `fct_stress_pulse.roa` last = 1.1698 | PASS | value correct |
| Stress Pulse | Industry ROA **caption** "FDIC QBP quarterly workbook" (0:429-430) | `stress_pulse_source_mode()` | **STALE/MISLEADING** | mode resolves to `"pending"`, not `"live"`, so caption falls to the QBP-workbook branch. But the 41 rows actually come live from DuckDB `fct_stress_pulse`, not a workbook. Caption misattributes the source. Root cause: qbp manifest `artifact_path` is a stale absolute path from another machine. Fix manifest path or treat DuckDB-backed rows as live. |
| Stress Pulse | Industry NIM `2.92%`, `QoQ +0.02 pts` (0:432-437) | `fct_stress_pulse.nim` 2.9191 vs 2.8957 | PASS | 2.9191→`2.92%`; delta +0.0234→`+0.02 pts` ✓ |
| Stress Pulse | Problem bank count → "Not published" + "Problem Bank List is not published in the current aggregate feed" (0:438-443) | `problem_banks` last = NULL | PASS | column all-NULL; honest fallback ✓ |
| Stress Pulse | Earnings chart (net_income bars + ROA line) (0:51-74,452) | `fct_stress_pulse` quarter/net_income/roa | PASS | columns present and populated |
| Stress Pulse | Funding panel falls back to NIM chart + "Funding-detail source gap" note (0:454-463) | `asset_yield`/`funding_cost` | PASS | both columns all-NULL → `has_chart_data` False → NIM fallback. Honest ✓ |
| Stress Pulse | Asset Quality chart (noncurrent_rate, nco_rate) (0:116-135,470) | `fct_stress_pulse` | PASS | both populated (e.g. 2025Q4 noncurrent 0.1565, nco 0.4047) |
| Stress Pulse | Unrealized Losses → empty_state "AFS and HTM ... not available" (0:477-489) | `afs_losses`/`htm_losses` | PASS | both all-NULL → empty branch. Honest ✓ |
| Stress Pulse | Recession bands `2020Q1-2020Q3`, `2023Q1-2023Q2` (0:33) | hardcoded design literal | PASS (acceptable) | static visual decoration, not a data claim. Note `2023Q1-2023Q2` is a stylistic call (no formal 2023 NBER recession); not a metric error. |
| Stress Pulse | "March 2023" annotation on unrealized-loss chart (0:166) | hardcoded; chart not rendered | N/A | inside `unrealized_losses_chart`, which is never called now (empty-state branch taken). Dead annotation. |
| Stress Pulse | Public-data snapshot block: "FDIC failures" 573, "Latest failure year" 2026, Unemployment, 10Y-2Y cards (0:289-385) | computed dynamically from `load_failures`/`_macro_panel` | N/A (DEAD CODE) | `render_public_data_stress_snapshot()` only runs when `frame.empty`; frame has 41 rows, so this entire block does not render. The values it *would* show are dynamic/correct, but it is currently unreachable. The selectbox `index=years.index(2010)` (0:344) hardcodes default year 2010, also unreachable. |
| Failure Forensics | Total failures `573`, `2000-2026, FDIC failed-bank list` (1:207-211,197-199) | `fct_bank_failures` count + min/max year | PASS | 573 rows; min 2000, max 2026 ✓ |
| Failure Forensics | Top state `GA`, `93 failures in current feed` (1:201-202,213) | value_counts on `state` | PASS | GA=93 ✓ |
| Failure Forensics | Latest failed bank `Metropolitan Capital Bank & Trust`, `2026-01-30` (1:203,214-219) | max `closing_date` row | PASS | matches DuckDB latest closing_date ✓ |
| Failure Forensics | Latest year count `1`, `2026 current slice` (1:200,220-221) | count where year=max(year) | PASS | 2026 has 1 failure ✓ |
| Failure Forensics | `resolution_type` = "Resolution detail not standardized in current feed" (1:33) | hardcoded literal | PASS (honest) | constant, not surfaced as a metric; never displayed in current table columns |
| Failure Forensics | State choropleth color basis (1:108-110) | `assets_millions` if any non-null else count | PASS | `assets_millions` all-NULL → falls back to `bank_id` count. Map shows failure counts (colorbar still labeled "Failures") ✓ |
| Failure Forensics | Acquirer chart top-15 (1:66-86) | `acquirer` column | PASS | 307 distinct acquirers exist; chart populated |
| Failure Forensics | Inventory table columns incl. Cert/Acquirer (1:130-145) | `fct_bank_failures` columns | PASS | columns present |
| Macro Transmission | 10Y-2Y card `0.51`, `As of 2026-04-23` (2:218-219) | DGS10-DGS2 latest shared date | PASS | 4.34-3.83=0.51, both at 2026-04-23 ✓ |
| Macro Transmission | Unemployment card `4.30%`, `As of 2026-03-01` (2:220-222) | UNRATE latest | PASS | 4.3 at 2026-03-01 ✓ |
| Macro Transmission | CPI card `330.29`, `As of 2026-03-01` (2:223-225) | CPIAUCSL latest | PASS | 330.293 at 2026-03-01 ✓ |
| Macro Transmission | Home Price Index card `326.61`, `As of 2026-01-01` (2:226-228) | CSUSHPINSA latest | PASS | 326.612 at 2026-01-01 ✓ |
| Macro Transmission | Failure overlay = monthly FDIC counts (2:75-93,139-170) | `fct_bank_failures.closing_date` monthly | PASS | derived live from failures |
| Macro Transmission | Indicator Board (Latest + "As of" per series) (2:96-120,262) | per-series dropna latest | PASS | each row uses its own latest non-null date; GDP "As of" would be 2025-10-01, others as above |

## Summary
- PASS: 23
- STALE/MISLEADING: 1
- WRONG: 0
- DEAD CODE (unreachable, not currently rendered): 3 items (snapshot block + its 2010-default selectbox; March-2023 annotation)

### Worst offender
**Stress Pulse ROA card caption** (0_Stress_Pulse.py:429-430): shows "FDIC QBP quarterly workbook" because `stress_pulse_source_mode()` returns `"pending"` instead of `"live"`. The 41 stress-pulse rows are served live from DuckDB, so the caption misattributes the data source. Cause is a cross-machine stale `artifact_path` in the qbp source manifest (`...\OneDrive\Documents\Projects\Creations\Live\FinLens\...`, nonexistent here). Either repair the manifest path so the mode resolves to `live`, or have the page key the caption off whether `fct_stress_pulse` actually returned rows rather than off the manifest.

### Notes (not failures)
- No hardcoded numeric metric literals are surfaced on rendered paths; all displayed numbers/dates/counts are computed from DuckDB at render time.
- Recession-band quarters are static visual design, acceptable.
- All "source gap" / "not published" / empty-state messages are honest reflections of all-NULL columns (problem_banks, asset_yield, funding_cost, afs_losses, htm_losses, assets_millions).
