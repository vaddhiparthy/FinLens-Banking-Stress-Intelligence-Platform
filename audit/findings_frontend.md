# Ceiling A (front-end) findings ledger

Evidence-backed. A finding is CLOSED only when a new artifact proves it.

| ID | Category | Page/Component | Severity | Evidence | Status | Description |
|----|----------|----------------|----------|----------|--------|-------------|
| A-001 | Accessibility | shared shell (top nav / section tabs, page_shell.py) | Blocker | audit/axe/*.json (1 critical each) | OPEN | `aria-allowed-attr` (critical), 2 nodes, on every page. An ARIA attribute is used on an element whose role does not allow it (likely the custom nav buttons). One fix in the shared shell should clear all 5 pages. Re-run axe to close. |
| A-002 | Hidden feature | AI surface | Blocker | audit/feature_inventory.md | OPEN | competing-risks / Fine-Gray, calibration bake-off, CBLR, B1 point-in-time, sequence_sweep built but not surfaced; route to AI Model Quality / Decisions. |
| A-003 | Hidden feature | DE surface | Blocker | audit/feature_inventory.md | OPEN | Great Expectations suite result + model-serving routes (/predict-failure-risk, Docker, kind) built but not surfaced; route to Data Engineering page (Data Quality / serving). |
| A-004 | Hidden feature | AI surface | Major | audit/feature_inventory.md | OPEN | Key docs (FAILURE_DECOMPOSITION, COMPETING_RISKS, RELATED_WORK, VALIDATION_REPORT) not linked; add popovers/links on the AI surface. |
| A-005 | Noise / dead code | DE page | Minor | audit/feature_inventory.md | OPEN | `anomaly_chart`, `architecture_components_frame` defined but unused; remove. |
| A-006 | Visual polish | AI Model Quality | Major | audit/screenshots/ai_engineering.png | OPEN | Long wall of charts, no hero result up top, deep validator charts not collapsed into expanders. |
| A-007 | Visual polish | AI Pipeline | Major | audit/screenshots/ai_engineering.png | OPEN | Pipeline section sparse, no flow diagram. |
| A-008 | Visual polish | shared shell | Major | audit/screenshots/*.png | OPEN | Active section tab uses disabled-grey, reads as broken not selected. |
| A-009 | Pending artifacts | all pages | Blocker | (none yet) | OPEN | Lighthouse per page, Playwright E2E results.xml (incl chatbot), journey.md, usefulness.md, interactive-state screenshots not yet generated. |

Reviewer sign-offs pending: ui-design, information-architecture, frontend, data-integrity, accessibility (audit/signoffs/).
