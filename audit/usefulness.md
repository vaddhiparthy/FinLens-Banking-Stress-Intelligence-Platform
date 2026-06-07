# Ceiling A: element usefulness classification

Per the audit mandate every element is classified USEFUL / KEEP / REDESIGN / REMOVE. A real
feature is never hidden to reduce noise; REMOVE is reserved for dead code and fabricated
placeholders. This pass is post-remediation, so most rows are settled.

## REMOVE (done)
| Element | Surface | Why | Status |
|---|---|---|---|
| `anomaly_chart()` | DE page | Hard-coded fabricated row-count series (142,141,…); not wired to any data | REMOVED (A-005) |
| `architecture_components_frame()` | DE page | Unused; superseded by `platform_stack_frame()` | REMOVED (A-005) |
| `_patch_popover_a11y` JS inject | shared shell | Traded one a11y violation for a nested-interactive one | REMOVED (A-001) |
| `web/` prototype | repo | Superseded static prototype, not part of the running app | Not surfaced (correctly excluded) |

## REDESIGN (done)
| Element | Surface | Change | Status |
|---|---|---|---|
| Surface-nav + paper triggers | shared shell / AI | `st.popover` → `st.expander` (fixes critical aria-allowed-attr) | DONE (A-001) |
| Active section tab | shared shell | Greyable underline → accent-tinted pill + 3px underline; reads as selected | DONE (A-008) |
| Model Quality deep blocks | AI | Wall of charts → metric hero + headline charts, deep validators in expanders | DONE (A-006) |
| AI Pipeline intro | AI | Bullet-only → 6-stage flow diagram with live metrics | DONE (A-007) |
| Analyst Assistant eval metrics | Business | Static copy → read from rag/eval_report.json | DONE |

## USEFUL — newly surfaced (was hidden, now shown)
| Element | Surface | Status |
|---|---|---|
| Calibration bake-off (isotonic vs Platt vs Venn-Abers) | AI / Model Quality | SURFACED (A-002) |
| 2020Q1 CBLR break robustness | AI / Model Quality | SURFACED (A-002) |
| Competing risks (cause-specific vs Fine-Gray) | AI / Model Quality | SURFACED (A-002) |
| Point-in-time vs restated inputs (B1) | AI / Model Quality | SURFACED (A-002) |
| Methodology write-ups (6 docs) | AI / Decisions | SURFACED (A-004) |
| Great Expectations suite result (20/20) | DE / Data Quality | SURFACED (A-003) |
| ML serving routes (/predict-failure-risk etc., :8077) | DE / Administration | SURFACED (A-003) |
| Containerization + kind k8s deploy recipe | DE / Administration | SURFACED (A-003) |

## KEEP (already well-placed, no change)
- All Business surfaces (Stress Pulse, Failure Forensics, Macro Transmission, Early Warning).
- DE: Live Pipeline Sankey + status table + data browser; Source Contracts; Engineering Stack;
  Architecture Decisions.
- AI: Notebook embed; Feature Contracts (SHAP + correlation + monotone table); ML Stack table;
  failure-type decomposition; pooled-vs-addressable; GRU challenger; drift; model card;
  administration code; Wiki.
- Analyst Assistant cached answer + live ask + trace caption.

## Signal-not-noise verdict
After remediation there is no fabricated or placeholder element reachable on the UI, no
real feature is hidden, and the densest surface (AI Model Quality) now has a clear hierarchy
(hero → headline charts → collapsed deep validators). Remaining open items are A-010 (Plotly
density performance) and A-011 (SEO meta), tracked in findings_frontend.md.
