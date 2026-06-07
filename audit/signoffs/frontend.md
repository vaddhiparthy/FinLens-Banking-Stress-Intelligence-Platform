# Ceiling A sign-off: frontend

VERDICT: PASS

ARTIFACTS REVIEWED:
- audit/playwright/results.xml — 8 testcases, 0 failures/skipped/errors, names map 1:1 to the spec's 8 tests.
- audit/e2e/surfaces.spec.mjs, axe-scan.mjs, playwright.config.mjs — read in full.
- audit/lighthouse/{home,ai_engineering,analyst_assistant,early_warning,data_engineering}.json — parsed category scores.
- audit/axe/{home,data_engineering,ai_engineering,analyst_assistant,early_warning}.json — parsed nViolations + impact filter.
- audit/findings_frontend.md — read in full.
- streamlit_app/pages/7_AI_Engineering.py, 4_Data_Engineering.py, lib/ml_charts.py, lib/page_shell.py, lib/theme.py — read in full.
- Commands run (independent verification, not trusting claims):
  - `.venv/Scripts/python.exe -c "import ast; ast.parse(...)"` on all 5 changed .py: all PARSE OK.
  - grep `anomaly_chart|architecture_components_frame` across repo: appears ONLY in audit/*.md, ZERO call sites or defs in any .py.
  - grep the 5 new ml_charts loaders (load_calibration_bakeoff, load_cblr_robustness, load_b1_compare, load_competing_risks, load_fine_gray) + 2 figs (cblr_variants_fig, calibration_bakeoff_fig) + pipeline_stage_flow in page 7: all referenced (loaders/figs defined in ml_charts.py and called from page 7's quality/pipeline sections).
  - parsed axe JSONs: 0 violations (0 serious/critical) on all 5 pages.
  - parsed lighthouse JSONs: home/AI/assistant/early-warning a11y 100, bp 96-100, seo 91, perf 85-87; DE perf 61 (run scoped onlyCategories=['performance']).
  - cross-checked the Ingest-stage hardcoded literals against ml/artifacts/{viz_pack,metrics_h4}.json and ml/scripts/generate_report.py.
  - confirmed pipeline_stage_flow/metric_card/section_heading/inject_styles defined in ui_components.py.
  - confirmed A-008 active-tab CSS targets `div[class*="st-key-tab_"] button:disabled` (theme.py:784-799) matching the section-tab button key `tab_{mode}_{key}_{active_page}` from page_shell._render_section_tabs.

BLOCKING ISSUES: none

NOTES:
1. Dead variable: 7_AI_Engineering.py:147 computes `_npanel` (n_train + n_oot) and never uses it. Harmless leftover; should be deleted. Not blocking.
2. Hardcoded panel literals at 7_AI_Engineering.py:151 ("448,661 bank-quarters", "~8,800 banks", "2008-2026Q1") are NOT artifact-loaded, but they are NOT fabricated: 448,661 / 8,803 banks is the documented labelable-panel figure also stated in ml/scripts/generate_report.py:261. They are static descriptive copy, distinct from the model train(416,095)+OOT(118,943) counts, and do not contradict any live metric. The genuinely artifact-driven flow metrics (66 OOT failures, 28-quarter holdout, PR-AUC, ECE) all read from viz_pack/metrics and were verified to match. Recommend wiring 448,661 to a panel artifact so it can't drift, but it is current and correct today.
3. DE lighthouse JSON has null a11y/bp/seo because that run was scoped to performance only (configSettings.onlyCategories=['performance']). Findings A-010 asserts DE "a11y 100, bp 96, seo 91"; those specific DE non-perf numbers are not re-proven by this JSON. However DE has 0 axe violations and the other 4 pages all score a11y 100 / bp 96-100 / seo 91, so the claim is plausible and consistent. Documentation-vs-artifact gap only, not a functional defect.
4. E2E assertions are substantive, not trivially-true: they assert real rendered strings per surface (Live Pipeline, Great Expectations Suite, Training & scoring pipeline, Serve + monitor, PR-AUC (OOT), Robustness & validation cross-checks, Methodology write-ups) and exercise interactive section-nav button clicks plus the Analyst Assistant cached-answer + Ask-live affordance. The artifact-gated blocks (GX suite, robustness cross-checks) rendering in the passing tests confirms the underlying artifacts are present.
5. No broken imports found; all symbols imported by the changed pages (mc.* figures/loaders, pipeline_stage_flow, set_meta_description, get_ai_section) resolve to real definitions.
