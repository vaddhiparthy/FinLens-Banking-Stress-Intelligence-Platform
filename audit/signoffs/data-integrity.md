# Ceiling A sign-off: data-integrity

VERDICT: PASS

ARTIFACTS REVIEWED:
- ml/artifacts/calibration_bakeoff.json
- ml/artifacts/cblr_robustness.json
- ml/artifacts/competing_risks.json
- ml/artifacts/fine_gray.json
- ml/artifacts/b1_compare.json
- great_expectations/validation_result.json
- rag/eval_report.json
- ml/finlens_ml/serve.py
- deploy/k8s/ml-serve.yaml, deploy/k8s/kind-config.yaml
- ml/Dockerfile, api/Dockerfile, Dockerfile.streamlit, airflow/Dockerfile, docker-compose.prod.yml
- streamlit_app/pages/7_AI_Engineering.py
- streamlit_app/lib/ml_charts.py
- streamlit_app/pages/4_Data_Engineering.py
- streamlit_app/pages/8_Analyst_Assistant.py

BLOCKING ISSUES: none

NOTES:
1. AI Model Quality robustness cross-checks all load via the ml_charts loaders, no hardcoded values.
   - calibration_bakeoff: load_calibration_bakeoff() -> calibration_bakeoff_fig reads ece (isotonic 0.00019, platt 0.00027, venn_abers 0.00066), winner "isotonic"; caption reads winner_stability.bootstrap_flip_rate (0.243) and conformal_feasibility.prediction_set_note. Matches artifact.
   - cblr_robustness: cblr_variants_fig reads variants[].pr_auc_addressable_threshold (0.2503 / 0.2503 / 0.0849) + CIs; caption reads cblr_break.mechanism, null_rate_2020plus (0.37), null_rate_2019 (0.003), and conclusion. The 0.165 drop cost = drop_feature_cost_addressable (0.1654), carried in the conclusion string. Matches artifact.
   - competing_risks / fine_gray: metric_cards show cause-specific PR-AUC 0.1755 CI [0.1004, 0.2813] and Fine-Gray 0.1824 CI [0.102, 0.2941] from fg["cause_specific"]/fg["fine_gray"]; CIF failure 0.18478 and merger 0.73867 from crisk["cumulative_incidence"]. Matches artifacts.
   - b1_compare: FDIC-restated 0.1755 CI [0.1004, 0.2813], originally-filed/point-in-time 0.1307 CI [0.0647, 0.2297], noncurrent_field_audit.note, and noncurrent_reconstruction.category_sum_vs_official_corr (0.968). Matches artifact.
2. DE Data Quality GX block reads great_expectations/validation_result.json via gx_validation() (preferring the uncommitted fresh run, falling back to the committed snapshot) and renders the suite header from n_success/n_expectations (20/20, success=true) plus per-expectation rows from results[] via gx_results_frame(). The 20/20 is loaded, not hardcoded; observed values (e.g. row count 448,661, max quarter 2026Q1, not-null rates) come straight from the file.
3. DE Administration ML serving routes match ml/finlens_ml/serve.py exactly: /predict-failure-risk, /predict, /predict/batch, /ready, /health. Deploy artifacts in deploy_artifacts_frame() all exist (ml/Dockerfile, api/Dockerfile, Dockerfile.streamlit, airflow/Dockerfile, docker-compose.prod.yml, deploy/k8s/kind-config.yaml, deploy/k8s/ml-serve.yaml). Port 8077, NodePort 30077, readinessProbe /ready, livenessProbe /health in ml-serve.yaml match both the UI caption and ml/Dockerfile (EXPOSE 8077, uvicorn finlens_ml.serve:app --port 8077).
4. Analyst Assistant RAG metrics read rag/eval_report.json via _eval_report()/_eval_caption(): hit@4 = 1.00, MRR = 0.92 (0.9167), citation-grounding = 1.00, n_questions = 20. Loaded, not static copy.
5. Cosmetic only (non-blocking): the k8s/Docker image name is "fulllens-ml-serve" while the app brands as FinLens/FullLens elsewhere. The UI deploy caption matches the actual manifest/Dockerfile, so it is internally consistent; just a naming inconsistency, not a data-integrity defect.
