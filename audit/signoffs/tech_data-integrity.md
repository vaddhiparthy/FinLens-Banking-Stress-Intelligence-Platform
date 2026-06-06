# Ceiling B sign-off: data-integrity

VERDICT: PASS

ARTIFACTS REVIEWED:
- audit/tech/data_provenance.md
- ml/artifacts/metrics_h4.json
- ml/artifacts/failure_decomposition.json
- ml/artifacts/pooled_vs_addressable.json
- ml/artifacts/cblr_robustness.json
- ml/artifacts/sequence_challenger.json
- ml/artifacts/viz_pack.json
- rag/eval_report.json
- ml/finlens_ml/failure_cause_labels.py
- streamlit_app/lib/wiki_ai_articles.py (_load_metric_values)
- streamlit_app/pages/7_AI_Engineering.py
- streamlit_app/pages/8_Analyst_Assistant.py
- streamlit_app/lib/ml_charts.py (artifact loaders)

BLOCKING ISSUES: none

NOTES:
1. Headline spot-checks all reconcile UI -> committed artifact, exactly:
   - PR-AUC 0.301: metrics_h4.oot_test.calibrated_lgbm.pr_auc = 0.30136; viz_pack.curves.pr_auc = 0.3014. The Model Quality tab formats t['pr_auc'] live (.3f -> 0.301); the wiki reads the same via _load_metric_values. Match.
   - Addressable 0.382 [0.250,0.530]: failure_decomposition.pr_auc_addressable = 0.3819, pr_auc_addressable_ci = [0.2499, 0.5296]. UI caption and ml_charts.addressable_pr_fig read these live. Match.
   - 66 OOT failures / 19 banks: metrics_h4.test_positives = 66, failure_decomposition.n_distinct_banks = 19, viz_pack.n_oot_failures = 66. Match.
   - Cross-model lift (5 families): pooled_vs_addressable.json carries monotone GBM, unconstrained GBM, penalized logit, random forest, XGBoost; every lift positive (+0.0406 to +0.0805). UI reads models live. Match.
   - RAG hit@4 = 1.0: rag/eval_report.json retrieval_hit_at_k = 1.0; citation_grounding_rate = 1.0. Match.

2. The ML/wiki surfaces are genuinely auto-synced, not hardcoded. wiki_ai_articles._load_metric_values() reads metrics_h4.json / viz_pack.json / failure_decomposition.json / sequence_challenger.json at import; 7_AI_Engineering.py and ml_charts.py load the artifacts directly (lru_cache loaders). No served ML number is a literal in the page code. Verified: no stale hardcoded headline values reachable.

3. failure_cause_labels.py: 19 banks, 18/19 with a primary regulator source (Treasury OIG / FDIC OIG / Fed / Fed OIG / OCC / FDIC PR or FAQ), one news-only case (Community Bank & Trust - West Georgia, no OIG report yet) flagged confidence "low" and source_type "news". Each entry carries a source_url and a one-line quote. URL conventions match the issuing agencies and the quotes are consistent with the public record (SVB Fed review, Heartland Tri-State Fed OIG MLR ~$47M pig-butchering, FDIC PR-23073 First Republic, OCC NR-2024-119 First National Bank of Lindsay, etc.). Cause counts reproduce: fundamental_credit 10, fraud 6, rate_liquidity 3; fraud -> invisible mapping yields the 19-bank-quarter external invisible set used in failure_decomposition.external_labels (agreement 0.9242). Note: source URLs could not be HTTP-validated from the sandbox (no network egress, all returned 000); they were judged real on document-identity and URL-convention grounds, not live fetch. Recommend a periodic external link-check, but this is not a fabrication.

4. The one hardcoded value found is benign: 8_Analyst_Assistant.py line 93 prints "hit@4 = 1.0, MRR = 0.92, citation-grounding = 1.0" as static copy rather than reading rag/eval_report.json. All three are accurate against the artifact (MRR 0.92 is 0.9167 rounded to 2dp). Not a blocker because the values are correct, but unlike the ML surface this string will not auto-update if the RAG eval is re-run. Recommend wiring it to the artifact for consistency with the no-stale-by-construction posture claimed in data_provenance.md.

5. Internal consistency across artifacts holds: metrics_h4 oot_test_ci.pr_auc_ci = [0.1908, 0.4380] = failure_decomposition.pr_auc_full_ci = pooled_vs_addressable monotone_gbm_served.pr_auc_pooled_ci = sequence_challenger.gbm_pr_auc_ci. Served PR-AUC 0.3014 is identical wherever it appears. The GRU 0.207 vs GBM 0.301 (delta -0.094), the CBLR robustness (0.250 native-null vs 0.250 indicator vs 0.085 drop), and the rolling backtest (10 folds, mean 0.2128) are all self-consistent and match the UI text in 7_AI_Engineering.py and ml_charts.py.

6. Provenance and freshness: served model frozen at commit 7473608 (exists in git history). data_provenance.md, all reviewed artifacts, the labels file, and rag/eval_report.json have no uncommitted modifications; the only dirty files in the working tree (.gitignore, ml_charts.py) do not alter any served value.
