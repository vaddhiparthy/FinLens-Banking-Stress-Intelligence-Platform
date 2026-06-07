# Ceiling A sign-off: information-architecture

VERDICT: PASS

ARTIFACTS REVIEWED:
- audit/feature_inventory.md (the HIDDEN list)
- audit/findings_frontend.md (A-002, A-003, A-004, A-005 closures)
- audit/usefulness.md, audit/journey.md
- streamlit_app/pages/7_AI_Engineering.py (AI surface, verified in code)
- streamlit_app/pages/4_Data_Engineering.py (DE surface, verified in code)
- streamlit_app/lib/ml_charts.py (new loaders + figures, verified in code)
- ml/artifacts/*.json + great_expectations/validation_result.json + deploy/k8s/* (verified on disk and structurally)

BLOCKING ISSUES: none

Every previously-HIDDEN real feature is now reachable on its correct surface, verified against the
running code (not the ledger's word):

ML cross-checks → AI / Model Quality (section == "quality", 7_AI_Engineering.py:580-662):
1. calibration_bakeoff — load_calibration_bakeoff() + calibration_bakeoff_fig (7_AI:594-605). JSON
   keys (calibration_bakeoff/winner/winner_stability/conformal_feasibility) match the renderer.
2. cblr_robustness — load_cblr_robustness() + cblr_variants_fig (7_AI:606-613). 3 variants present.
3. competing_risks — load_competing_risks() (7_AI:631-639). cumulative_incidence +
   informative_censoring present.
4. fine_gray — load_fine_gray() (7_AI:614-630). cause_specific/fine_gray/interpretation present.
5. b1_compare — load_b1_compare() (7_AI:640-662). point_in_time.oot + fdic_restated.oot +
   noncurrent_field_audit + noncurrent_reconstruction all present.
6. sequence_sweep — surfaced via sequence_challenger.robustness_sweep (7_AI:545-551); n_configs=6,
   oot range 0.1886–0.2458 render. (The standalone sequence_sweep.json was always redundant; the
   sweep numbers reach the UI through the challenger artifact, so nothing is hidden.)

Methodology write-ups → AI / Model Decisions (section == "decisions", 7_AI:689-705): 6 docs
(FAILURE_DECOMPOSITION, COMPETING_RISKS, B1_POINT_IN_TIME, SEQUENCE_CHALLENGER, VALIDATION_REPORT,
RELATED_WORK) as expanders. Correct surface (AI narrative on AI).

Data quality / serving / infra → DE (verified section boundaries via get_technical_section dispatch):
7. Great Expectations result → DE / Data Quality (active_section == "status" starts 4_DE:1214; GX
   block 4_DE:1233-1251). validation_result.json is committed and reads success=True, 20/20.
8. /predict-failure-risk + /predict + /predict/batch + /ready → DE / Administration (active_section
   == "administration" starts 4_DE:1345; service_endpoints_frame at 4_DE:982-1029, rendered 1351).
9. Docker (4 Dockerfiles + compose) + kind/k8s (kind-config.yaml + ml-serve.yaml) → DE /
   Administration (deploy_artifacts_frame 4_DE:786-806, rendered 1373; recipe 1368-1377). Both
   deploy/k8s files exist on disk.

Dead code (A-005): anomaly_chart and architecture_components_frame have zero matches anywhere in
streamlit_app/ — both definitions and all call sites are gone. Correctly REMOVED, not hidden.

Surface-correctness check: every ML/model artifact lands on the AI surface; every data-quality,
model-serving-API, container, and Kubernetes artifact lands on the DE surface. No ML content stuffed
onto DE and no infra/DE content stuffed onto AI. The serving routes are on DE (correct: they are an
operational/serving concern presented in the DE control room alongside the other endpoint catalog
and the deploy recipe), while the model science stays on AI.

Tab/section organization is coherent: AI keeps its 7 in-page sections (deep validators collapsed
into expanders under Model Quality so the hero leads), DE keeps its 6 sections with GX beside the
dbt quality outcomes and serving+deploy beside the existing endpoint/control-plane administration
content.

NOTES:
1. sequence_sweep.json as a standalone file is still not read by the UI, but this is not a hidden
   feature: the identical sweep numbers are surfaced through sequence_challenger.robustness_sweep.
   No information loss, so not blocking.
2. Several pure process/engineering docs (CEILING_BACKLOG, FINAL_SIGNOFF, PUBLICATION_READINESS,
   RUN_LOCAL, ADRs, mkdocs config, the superseded web/ prototype) remain unsurfaced. These are not
   product features; surfacing build-process scaffolding on a presentation surface would be wrong,
   so their absence is correct, not a HIDDEN-feature violation.
3. DE Administration also still does not list the DE-app FastAPI /failures, /banks/{id},
   /metrics/{series_id} routes. These are out of scope for this sign-off (not on the cross-check
   list) and are minor catalog completeness, not a hidden flagship feature; noted for tracking only.
