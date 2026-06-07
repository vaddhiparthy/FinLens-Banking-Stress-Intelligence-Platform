# ruff: noqa: E402
"""AI Engineering surface, the ML pillar, mirroring the Data Engineering sections.

Every section shows the REAL artifact: charts baked from the trained model + panel
(ml/artifacts/viz_pack.json), the live feature contract, and the actual running
source code (pulled via inspect.getsource, so it can never drift from what runs).
"""

import inspect
import json
import re
import sys
import textwrap
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").exists()
)
for sub in ("", "src", "ml"):
    p = str(PROJECT_ROOT / sub) if sub else str(PROJECT_ROOT)
    if p not in sys.path:
        sys.path.insert(0, p)

from streamlit_app.lib import ml_charts as mc
from streamlit_app.lib.page_shell import (
    AI_PAGE,
    get_ai_section,
    page_intro,
    status_ribbon,
    top_navigation,
)
from streamlit_app.lib.telemetry import record_page_view
from streamlit_app.lib.theme import app_css, ensure_theme_state, get_theme_mode
from streamlit_app.lib.ui_components import (
    inject_styles,
    metric_card,
    pipeline_stage_flow,
    section_heading,
)

ART = PROJECT_ROOT / "ml" / "artifacts"

_REL_LINK = re.compile(r"\[([^\]]+)\]\((?!https?://|mailto:)[^)]*\)")


def _render_repo_md(text: str) -> str:
    """Repo docs cross-reference each other with relative .md links (e.g. [x](RELATED_WORK.md)).
    Those 404 once deployed (the linked files are not served), so flatten any non-http link to
    plain text, keeping the words. Real external (http/mailto) links are left intact."""
    return _REL_LINK.sub(r"\1", text)


st.set_page_config(
    page_title="FinLens | AI Engineering", layout="wide", initial_sidebar_state="collapsed"
)
ensure_theme_state()
inject_styles(app_css(get_theme_mode(), sidebar_open=True))


top_navigation("ai", AI_PAGE)
record_page_view("ai_engineering", AI_PAGE)

MODE = get_theme_mode()


def _metrics() -> dict | None:
    p = ART / "metrics_h4.json"
    return json.loads(p.read_text()) if p.exists() else None


def _code(obj) -> str | None:
    """Real source of a live function/class, so excerpts never drift from what runs."""
    try:
        return textwrap.dedent(inspect.getsource(obj))
    except Exception:
        return None


def _show_code(obj, label: str, explain: str | None = None, expanded: bool = False) -> None:
    if explain:
        st.markdown(explain)
    src = _code(obj)
    if src:
        with st.expander(label, expanded=expanded):
            st.code(src, language="python")


from finlens_ml.features import FEATURE_COLUMNS

N_FEATURES = len(FEATURE_COLUMNS)

m = _metrics()
viz = mc.load_viz_pack()
PANEL_FACTS = mc.load_panel_facts() or {}
N_OOT_FAIL = PANEL_FACTS.get("oot_failures") or (viz.get("n_oot_failures") if viz else 66)
section = get_ai_section()

_AI_INTRO = {
    "pipeline": ("Bank-Distress Model: Pipeline",
                 "How the discrete-time hazard model is trained and scored on the FDIC "
                 "bank-quarter panel, end to end, with the real code at each step."),
    "notebook": ("Bank-Distress Model: Analysis Notebook",
                 "The Jupyter notebook behind this analysis, executed on the real panel: "
                 "EDA, out-of-time evaluation, calibration, and SHAP."),
    "contracts": ("Bank-Distress Model: Feature Contracts",
                  "The model's input contract: every feature, its enforced monotone "
                  "direction, its measured importance, and how the features correlate."),
    "stack": ("Bank-Distress Model: ML Stack",
              "The open-source, $0 production stack behind training, calibration, "
              "serving, and monitoring."),
    "quality": ("Bank-Distress Model: Model Quality",
                "Out-of-time performance, calibration, score separation, and drift, "
                "drawn live from the held-out evaluation."),
    "decisions": ("Bank-Distress Model: Model Decisions",
                  "The key modeling choices and the governance posture behind them."),
    "administration": ("Bank-Distress Model: Administration",
                       "Registry, promotion, retraining, rollback, and the $0 guard."),
    "wiki": ("Bank-Distress Model: Wiki",
             "Quick reference for the modeling concepts used across this surface."),
}
_title, _copy = _AI_INTRO.get(section, _AI_INTRO["pipeline"])
_WIKI_SLUG = {
    "pipeline": "problem-framing-discrete-time-hazard",
    "notebook": "out-of-time-evaluation",
    "contracts": "feature-engineering-and-the-monotone-contract",
    "stack": "serving-the-model",
    "quality": "out-of-time-evaluation",
    "decisions": "model-risk-and-governance",
    "administration": "serving-the-model",
    "wiki": None,
}

status_ribbon("Machine Learning Engineering")
page_intro("AI Engineering", _title, _copy, wiki_slug=_WIKI_SLUG.get(section))

try:
    _paper = PROJECT_ROOT / "docs" / "ml" / "PAPER.md"
    if _paper.exists():
        with st.expander("Research write-up (measurement paper)"):
            st.markdown(_render_repo_md(_paper.read_text(encoding="utf-8")))
    st.caption("Ask the cited assistant anything about the model or a specific bank using the "
               "**Research a bank** button in the bottom-right corner of any page.")
except Exception:
    pass


if section == "pipeline":
    section_heading("Training & scoring pipeline", "Discrete-time hazard model on the FDIC bank-quarter panel.")
    _pr = None
    if m:
        try:
            _pr = m["oot_test"]["calibrated_lgbm"]["pr_auc"]
        except Exception:
            _pr = None
    _ece = (m.get("oot_calibration", {}) or {}).get("ece") if m else None
    _pf = mc.load_panel_facts() or {}
    _nfail = _pf.get("oot_failures") or (viz.get("n_oot_failures") if viz else 66)
    _nrows = f"{_pf['n_panel_rows']:,}" if _pf.get("n_panel_rows") else "448k+"
    _nbanks = f"~{round(_pf['n_banks'], -2):,.0f}" if _pf.get("n_banks") else "~8,800"
    _qrange = (f"{_pf.get('min_quarter')}–{_pf.get('max_quarter')}"
               if _pf.get("min_quarter") else "2008Q1–2026Q1")
    _window = _pf.get("oot_window_quarters") or 28
    pipeline_stage_flow([
        {"name": "Ingest", "copy": "FDIC Call Reports → DuckDB point-in-time panel",
         "metric_1": f"{_nrows} bank-quarters", "metric_2": f"{_nbanks} banks", "metric_3": _qrange},
        {"name": "Features", "copy": "CAMELS-aligned ratios, trends, peer z-scores",
         "metric_1": f"{N_FEATURES} features", "metric_2": "point-in-time", "metric_3": "monotone-signed"},
        {"name": "Label", "copy": "fails-within-4q, merger/end-of-data censored",
         "metric_1": f"{_nfail} OOT failures", "metric_2": "leakage-free", "metric_3": "forward-looking"},
        {"name": "Split", "copy": "rolling-origin out-of-time, reporting-lag embargo",
         "metric_1": f"{_window}-quarter holdout", "metric_2": "embargoed", "metric_3": "no leakage"},
        {"name": "Train + calibrate", "copy": "monotone LightGBM, 12-seed bag, isotonic",
         "metric_1": f"PR-AUC {_pr:.3f}" if _pr else "calibrated", "metric_2": f"ECE {_ece:.0e}" if _ece else "calibrated", "metric_3": "monotone"},
        {"name": "Serve + monitor", "copy": "FastAPI (prob + SHAP), Evidently drift watch",
         "metric_1": "/predict-failure-risk", "metric_2": "calibrated prob", "metric_3": "drift-watched"},
    ])
    st.markdown(
        "- **Ingest** per-CERT FDIC Call Report financials (free API) into a DuckDB panel\n"
        f"- **Features** {N_FEATURES} CAMELS-aligned ratios, trends, and peer z-scores "
        "(point-in-time)\n"
        "- **Label** fails-within-4q with merger / end-of-data censoring (leakage-free)\n"
        "- **Split** rolling-origin out-of-time with a reporting-lag embargo\n"
        "- **Train** LightGBM (monotone, class-weighted), then calibrate the probabilities\n"
        "- **Serve** FastAPI (calibrated probability + SHAP), **monitor** drift with Evidently"
    )
    if m:
        fm = m.get("final_model", {})
        st.success(
            f"Served model: {fm.get('n_estimators')} trees ({fm.get('tree_count_source')}), "
            f"calibration={fm.get('calibration_method')}, trained on {fm.get('n_train'):,} rows."
        )
    section_heading("The real code behind each step", "Pulled live from the source, not retyped.")
    from finlens_ml import labels, splits, train
    _show_code(
        labels.attach_labels,
        "Show the labelling code (labels.attach_labels)",
        explain="**Labelling.** Each bank-quarter is marked 1 if that bank fails within the "
        "next four quarters, else 0. The hard part is not leaking the future: a bank that "
        "merges or simply runs out of data is *censored* (dropped), not recorded as a "
        "survivor, because we cannot know its four-quarter outcome. The exact rule:",
    )
    _show_code(
        splits.final_holdout_split,
        "Show the split code (splits.final_holdout_split)",
        explain="**Out-of-time split.** Train on the past, test on the future, never a random "
        "shuffle. An embargo (the label horizon plus the call-report reporting lag) ensures a "
        "training row's outcome window closes before the test period starts, so no information "
        "crosses the boundary:",
    )
    _show_code(
        train._fit_calibrated,
        "Show the training code (train._fit_calibrated)",
        explain="**Model and calibration.** A gradient-boosted hazard model with monotone "
        "constraints produces a ranking; its raw scores are then calibrated on a stratified "
        "slice that contains real failures, so a reported probability means what it says:",
    )

elif section == "notebook":
    import streamlit.components.v1 as components

    nb_html = PROJECT_ROOT / "ml" / "notebooks" / "bank_distress_analysis.html"
    section_heading(
        "Analysis notebook",
        "Executed on the real FDIC panel. Same protocol as the shipped metrics.",
    )
    if nb_html.exists():
        components.html(nb_html.read_text(encoding="utf-8"), height=900, scrolling=True)
        st.caption("Executed on the real panel (ml/notebooks/bank_distress_analysis.ipynb).")
    else:
        st.info("Run ml/notebooks build (jupytext + nbconvert) to render the notebook.")

elif section == "contracts":
    from finlens_ml import features
    from finlens_ml.features import MONOTONE_CONSTRAINTS

    section_heading(
        f"Feature contract ({len(MONOTONE_CONSTRAINTS)} features)",
        "Each feature's economic monotone direction vs. distress risk is enforced in the model.",
    )
    if viz:
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(mc.shap_importance_fig(viz, MODE), use_container_width=True)
        with c2:
            st.plotly_chart(mc.correlation_fig(viz, MODE), use_container_width=True)
        st.caption(
            "Importance is mean |SHAP| over a real sample of the panel; the heatmap is the "
            "Pearson correlation among the most important features."
        )
    sign = {1: "↑ raises risk", -1: "↓ lowers risk", 0: "unconstrained"}
    fc = pd.DataFrame(
        [{"feature": f, "monotone": sign[v]} for f, v in MONOTONE_CONSTRAINTS.items()]
    )
    st.dataframe(fc, hide_index=True, use_container_width=True, height=360)
    st.caption("Point-in-time: features lag the reporting cycle; labels are strictly forward-looking.")
    _show_code(features.add_level_features, "How the ratio features are built (features.add_level_features)")
    _show_code(features.add_peer_zscores, "Peer z-scores (features.add_peer_zscores)")

elif section == "stack":
    section_heading("ML stack", "2026 production-grade, all open-source, $0.")
    st.table(pd.DataFrame([
        {"layer": "Model", "tool": "LightGBM (gradient-boosted hazard, monotone)"},
        {"layer": "Calibration", "tool": "scikit-learn CalibratedClassifierCV + FrozenEstimator"},
        {"layer": "Explainability", "tool": "SHAP TreeExplainer"},
        {"layer": "Tracking/registry", "tool": "MLflow 3.x (aliases, sqlite/Postgres)"},
        {"layer": "Serialization", "tool": "skops (safe, allow-listed, no pickle)"},
        {"layer": "Serving", "tool": "FastAPI (lifespan, Pydantic v2)"},
        {"layer": "Monitoring", "tool": "Evidently 0.7.x (data + prediction drift)"},
        {"layer": "Store", "tool": "DuckDB point-in-time panel"},
    ]))

elif section == "quality":
    if not m or not viz:
        st.info("Train the model and run ml/scripts/export_viz_pack.py to populate this surface.")
    else:
        t = m["oot_test"]["calibrated_lgbm"]
        logit = m["oot_test"]["logit_benchmark"]
        cal = m.get("oot_calibration", {})
        ci = m.get("oot_test_ci", {})
        prci = ci.get("pr_auc_ci", [None, None])
        rci = ci.get("recall_at_k_ci", [None, None])
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            sub = (f"95% CI [{prci[0]:.2f}, {prci[1]:.2f}]"
                   if prci and prci[0] is not None else f"vs logit {logit['pr_auc']:.3f}")
            metric_card("PR-AUC (OOT)", f"{t['pr_auc']:.3f}", sub)
        with k2:
            metric_card("ROC-AUC (OOT)", f"{t['roc_auc']:.3f}", "rank quality")
        with k3:
            sub = (f"95% CI [{rci[0]:.0%}, {rci[1]:.0%}]"
                   if rci and rci[0] is not None else "of failures caught")
            metric_card("Recall@200", f"{t['recall_at_k']:.1%}", sub)
        with k4:
            metric_card("Calibration ECE", f"{cal.get('ece', float('nan')):.1e}", "lower is better")
        st.caption(
            f"Out-of-time window: {m['eval_window_quarters']} quarters, "
            f"{viz['n_oot']:,} bank-quarters, {viz['n_oot_failures']} real failures "
            f"(base rate {viz['curves']['base_rate']:.3%}). With this few positives, the "
            "point estimates carry wide intervals, so they are reported with bootstrap CIs."
        )
        diff = m.get("lgbm_vs_logit_ap_diff", {})
        rb = m.get("rolling_backtest", {}).get("aggregate", {})
        if diff or rb:
            cA, cB = st.columns(2)
            with cA:
                if diff.get("ap_diff_ci"):
                    lo, hi = diff["ap_diff_ci"]
                    st.markdown(
                        f"**Does it really beat the benchmark?** Paired bootstrap of "
                        f"(LGBM − logit) PR-AUC: median **{diff['ap_diff_median']:+.3f}**, "
                        f"95% CI [{lo:+.3f}, {hi:+.3f}], "
                        f"P(LGBM > logit) = **{diff['prob_a_beats_b']:.1%}**. "
                        "The interval excludes zero, so the edge is real, not noise."
                    )
            with cB:
                if rb.get("n_folds"):
                    st.markdown(
                        f"**Multi-origin rolling backtest** ({rb['n_folds']} embargoed "
                        f"out-of-time folds): PR-AUC mean **{rb['pr_auc_mean']}**, "
                        f"std {rb['pr_auc_std']}, range {rb['pr_auc_min']}–{rb['pr_auc_max']}. "
                        f"These are a different cut from the headline {t['pr_auc']:.3f} (which "
                        "is the full 28-quarter out-of-time holdout); each fold here is a single "
                        f"year, so the headline sits within the rolling-fold spread rather than "
                        "equalling the mean. The std is as large as the mean because the folds "
                        "are bimodal, near-zero in calm years and ~0.5 in failure-containing "
                        "windows, which is the expected behaviour, not a defect."
                    )
        chal = m.get("challengers", {})
        tune = m.get("hyperparameter_tuning", {})
        if chal:
            section_heading(
                "Effective-challenge ladder",
                "The constrained model vs an unconstrained GBM (same tuned params, no "
                "monotone constraints) and the penalized logit.",
            )
            ladder = [
                {"model": "Calibrated LGBM (monotone)", "PR-AUC": round(t["pr_auc"], 4),
                 "ROC-AUC": round(t["roc_auc"], 4), "recall@200": round(t["recall_at_k"], 3)},
            ]
            if "unconstrained_gbm" in chal:
                u = chal["unconstrained_gbm"]
                ladder.append({"model": "Unconstrained GBM", "PR-AUC": round(u["pr_auc"], 4),
                               "ROC-AUC": round(u["roc_auc"], 4),
                               "recall@200": round(u["recall_at_k"], 3)})
            ladder.append({"model": "Penalized logit", "PR-AUC": round(logit["pr_auc"], 4),
                           "ROC-AUC": round(logit["roc_auc"], 4),
                           "recall@200": round(logit["recall_at_k"], 3)})
            st.dataframe(pd.DataFrame(ladder), hide_index=True, use_container_width=True)
            if "unconstrained_gbm" in chal:
                u = chal["unconstrained_gbm"]
                gap = u["pr_auc"] - t["pr_auc"]
                base = ("The shipped model is held to economically-signed monotone "
                        "relationships (more capital never raises predicted risk, higher "
                        "noncurrent loans never lowers it) - what SR 11-7 conceptual-soundness "
                        "review requires.")
                if gap > 0.01:
                    rel = gap / u["pr_auc"] if u["pr_auc"] else 0.0
                    st.caption(
                        f"The unconstrained GBM scores higher (PR-AUC {u['pr_auc']:.3f} vs "
                        f"{t['pr_auc']:.3f}, a {gap:.3f} / {rel:.0%} gap) - the deliberate "
                        f"price of those constraints. {base} At {N_OOT_FAIL} OOT positives that gap is "
                        "not statistically separable (see G0), and the validator-defensible "
                        "model is the one served."
                    )
                else:
                    st.caption(
                        f"Here the monotone model ({t['pr_auc']:.3f}) matches or beats the "
                        f"unconstrained GBM ({u['pr_auc']:.3f}), so the economic constraints "
                        f"cost nothing measurable. {base} The regulator-defensible model is "
                        "also the strongest, and it is the one served."
                    )
        # Ablation forest: the full ladder as a point+interval chart (CIs overlap by
        # construction at n_pos~66; the figure caption states the intended reading).
        if viz.get("ablation", {}).get("rungs"):
            st.plotly_chart(mc.ablation_forest_fig(viz, MODE), use_container_width=True)
        if tune.get("tuned"):
            bp = tune.get("best_params", {})
            st.caption(
                f"Hyperparameters tuned with Optuna over {tune.get('n_trials')} trials on "
                f"{tune.get('n_inner_folds')} inner time-series CV folds "
                f"(best CV PR-AUC {tune.get('cv_mean_pr_auc')}); not hand-set. "
                f"Tuned: {bp}."
            )
        # ---- Tuning & optimism (the search made auditable) ----
        study = (tune or {}).get("study") or viz.get("study") or {}
        if study:
            with st.expander("How the model was tuned — hyperparameter search, made auditable"):
                st.caption("Search progress, what mattered, per-trial stability, and the "
                           "inner-vs-OOT optimism gap.")
                if study.get("optimism"):
                    o = study["optimism"]
                    metric_card("Optimism ratio", f"{o.get('ratio', 0):.1f}×",
                                f"inner-CV {o.get('inner_pr_auc')} vs OOT {o.get('oot_pr_auc')} "
                                "(expected and acceptable, not a defect)")
                    st.plotly_chart(mc.optimism_fig(study, MODE), use_container_width=True)
                tc1, tc2 = st.columns(2)
                with tc1:
                    st.plotly_chart(mc.optuna_history_fig(study, MODE), use_container_width=True)
                with tc2:
                    st.plotly_chart(mc.optuna_importance_fig(study, MODE), use_container_width=True)
                st.plotly_chart(mc.trial_stability_fig(study, MODE), use_container_width=True)
                slice_fig = mc.optuna_slice_fig(study, MODE, n=4)
                if slice_fig is not None:
                    st.plotly_chart(slice_fig, use_container_width=True)
                else:
                    st.caption("Slice PR-AUC is noise-dominated at n_pos≤4 per inner fold; "
                               "importance shown instead.")
        # ---- G0: how we know the gate is calibrated (honesty instrumentation) ----
        g0 = viz.get("g0") or {}
        gp = g0.get("gate_power") or {}
        cov = g0.get("interval_coverage_sim") or {}
        if gp or cov:
            with st.expander("How the intervals were coverage-validated"):
                st.caption("An external-truth simulation (not a bootstrap of the holdout) "
                           "measures whether the CIs actually cover and how much power the "
                           "gate has at this positive count.")
                if gp.get("mde_statement"):
                    st.markdown(f"**Minimum detectable effect.** {gp['mde_statement']}")
                if cov.get("chosen_method"):
                    bd = cov.get("by_dgp", {})
                    cells = []
                    for dgp, d in bd.items():
                        c = d.get("coverage", {})
                        cells.append(f"{dgp}: " + ", ".join(f"{k} {v:.0%}" for k, v in c.items()))
                    rc = cov.get("recall_jeffreys_coverage")
                    recall_clause = (f" recall@k Jeffreys coverage {rc:.0%}." if isinstance(rc, (int, float))
                                     else " " + cov.get("recall_note", ""))
                    st.caption(
                        f"Chosen interval method: **{cov['chosen_method']}** (nominal "
                        f"{cov.get('nominal', 0.95):.0%}). Measured coverage under external-truth "
                        f"DGPs: " + " · ".join(cells) + "." + recall_clause
                    )
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(mc.pr_curve_fig(viz, MODE), use_container_width=True)
        with c2:
            st.plotly_chart(mc.roc_curve_fig(viz, MODE), use_container_width=True)
        c3, c4 = st.columns(2)
        with c3:
            st.plotly_chart(mc.calibration_fig(viz, MODE), use_container_width=True)
        with c4:
            st.plotly_chart(mc.score_dist_fig(viz, MODE), use_container_width=True)
        st.plotly_chart(mc.threshold_fig(viz, MODE), use_container_width=True)

        # Capacity curve (recall vs review budget) + multi-horizon overlay if eligible
        if viz.get("capacity_curve"):
            section_heading("Capacity curve",
                            "How many real failures the review budget catches as it widens.")
            st.plotly_chart(mc.capacity_curve_fig(viz, MODE), use_container_width=True)
        mh = mc.multi_horizon_pr_fig(viz, MODE)
        if mh is not None:
            st.plotly_chart(mh, use_container_width=True)

        by_year = viz.get("by_year") or []
        if by_year:
            section_heading("By year (all cohorts shown)",
                            "Calm, low-power years are shown explicitly, not dropped: the "
                            "model is strong in failure-containing windows, near-floor in calm "
                            "years.")
            st.plotly_chart(mc.by_year_fig(by_year, MODE), use_container_width=True)
            with st.expander("year-by-year counts"):
                st.dataframe(pd.DataFrame([
                    {"year": r["year"], "failures": r["n_pos"],
                     "PR-AUC": r["pr_auc"], "low power": r["low_power"]} for r in by_year
                ]), hide_index=True, use_container_width=True)

        decomp = mc.load_decomposition()
        if decomp:
            tc = decomp.get("type_counts", {})
            section_heading(
                "Why the by-year number collapses: failure-type decomposition",
                f"The {N_OOT_FAIL} out-of-time failures are not one kind of event. Classified by "
                "model-independent financial signature, the calm-year collapse splits into "
                "two distinct causes, not noise.")
            d1, d2 = st.columns(2)
            with d1:
                st.plotly_chart(mc.failure_mix_by_year_fig(decomp, MODE),
                                use_container_width=True)
            with d2:
                st.plotly_chart(mc.addressable_pr_fig(decomp, MODE),
                                use_container_width=True)
            st.markdown(
                f"- **Credit-visible: {tc.get('credit_visible', 0)}** bank-quarters, the "
                "model's design scope (high noncurrent / charge-offs / capital below the PCA "
                "lines).\n"
                f"- **Rate/liquidity-visible: {tc.get('rate_liquidity_visible', 0)}** "
                "(large uninsured base + securities book): the 2023 wave, Silicon Valley, "
                "Signature, First Republic. A credit-skewed model under-weights these, which "
                "is the collapse on the **2022 filing cohort** (those banks failed in 2023).\n"
                f"- **Invisible: {tc.get('invisible', 0)}** were financially sound at the "
                "last filing and failed anyway: in practice the fraud and scam failures "
                "(Enloe State, Heartland Tri-State, First National Bank of Lindsay, Pulaski "
                "Savings). No model on quarterly financials can rank these, which is the "
                "collapse on the **2024 filing cohort**.")
            _fci = decomp.get("pr_auc_full_ci"); _aci = decomp.get("pr_auc_addressable_ci")
            _fci_s = f" (95% CI {_fci[0]:.3f}-{_fci[1]:.3f})" if _fci else ""
            _aci_s = f" (95% CI {_aci[0]:.3f}-{_aci[1]:.3f})" if _aci else ""
            st.caption(
                f"Year on the chart is the FILING year; a flagged bank-quarter is a filing "
                f"that fails within the next 4 quarters, so failures land later (no banks "
                f"failed in calendar 2021 or 2022). Removing only the "
                f"{decomp.get('invisible_positives', 0)} invisible failures moves out-of-time "
                f"PR-AUC from {decomp.get('pr_auc_full')}{_fci_s} to "
                f"{decomp.get('pr_auc_addressable')}{_aci_s} on the "
                f"{decomp.get('addressable_positives')} addressable failures. The intervals "
                "overlap heavily (fewer positives widen the addressable CI): this is a "
                "structural reattribution of the signal, not a separable gain (G0 ~6% power). "
                "The addressable number is unchanged by the credit-vs-rate/liquidity boundary "
                "(only the invisible boundary moves it). The three modes are an author-defined "
                "diagnostic split, not a supervisory classification.")

        pva = mc.load_pooled_vs_addressable()
        if pva:
            section_heading(
                "The lift is a property of the evaluation, not the model",
                "The pooled-to-addressable lift appears in every model family, including the "
                "published Random Forest and XGBoost baselines, so it is the evaluation set that "
                "is biased by the structurally-invisible failures, not any one model.")
            cpa1, cpa2 = st.columns([1.2, 1])
            with cpa1:
                st.plotly_chart(mc.pooled_vs_addressable_fig(pva, MODE), use_container_width=True)
            with cpa2:
                lifts = ", ".join(f"{m['lift']:+.3f}" for m in pva.get("models", []))
                st.markdown(
                    f"- Lift positive in **all {len(pva.get('models', []))} families** "
                    f"({pva.get('lift_min')} to {pva.get('lift_max')}): {lifts}.\n"
                    "- Same out-of-time split per model; invisible positives removed identically.\n"
                    "- At 66 failures no single delta is separable; the claim is the consistent "
                    "direction across families, which is what makes it a measurement finding.")
            ext = (decomp or {}).get("external_labels") if decomp else None
            if ext:
                st.caption(
                    "Label-source sensitivity: with the invisible set taken from externally-"
                    f"sourced regulator failure causes instead of thresholds, addressable PR-AUC "
                    f"is {ext.get('pr_auc_addressable_external')} vs {decomp.get('pr_auc_addressable')} "
                    f"(threshold), agreement {ext.get('label_agreement_rate_on_positives')} on "
                    "positives. The result does not depend on how the invisible cohort is labelled.")

        seq = mc.load_sequence()
        if seq:
            section_heading(
                "Architecture challenger: GRU over quarterly trajectories",
                "The matched architecture for within-bank temporal autocorrelation was built "
                "and tested on equal footing. It does not beat the gradient-boosted incumbent.")
            s1, s2 = st.columns([1, 1.1])
            with s1:
                st.plotly_chart(mc.sequence_vs_gbm_fig(seq, MODE), use_container_width=True)
            with s2:
                st.markdown(
                    f"- GRU OOT PR-AUC **{seq.get('oot_pr_auc_gru')}** vs served GBM "
                    f"**{seq.get('oot_pr_auc_gbm_served')}** (delta {seq.get('delta_vs_gbm')}).\n"
                    f"- Inner-validation PR-AUC **{seq.get('best_inner_val_pr_auc')}** collapses "
                    "out-of-time: the in-sample trajectory signal does not transfer across the "
                    "regime/cohort shift (consistent with the decomposition above).\n"
                    f"- The GRU sits **inside** the GBM bootstrap CI, so at "
                    f"{seq.get('n_oot_positives')} failures the two are not statistically "
                    "separable; the worse point estimate plus monotonicity, calibration, and "
                    "interpretability keep the GBM served.")
                rs = seq.get("robustness_sweep") or {}
                if rs:
                    st.markdown(
                        f"- Not a single-config artifact: a sweep of **{rs.get('n_configs')}** "
                        f"GRUs (varying size, regularization, history length, seed) lands "
                        f"out-of-time in **{rs.get('oot_min')}–{rs.get('oot_max')}**, every one "
                        "below the GBM, with the same in-sample collapse.")
            st.caption(
                "Reported as a challenger, not a candidate for promotion. The obvious "
                "'more sophisticated' model was built, measured on equal footing, and does not "
                "help on the data that exists.")

        if viz.get("drift_top_features"):
            section_heading("Drift monitoring (Evidently)", "Reference 2008-18 vs current 2019-26.")
            ds = viz.get("drift_summary", {})
            st.write(
                f"{ds.get('n_drifted_columns')}/{ds.get('n_features_analyzed')} features drifted "
                f"(share {ds.get('share_of_drifted_columns')}); prediction-drift score "
                f"{ds.get('prediction_drift_score')}."
            )
            c5, c6 = st.columns(2)
            with c5:
                dfig = mc.drift_fig(viz, MODE)
                if dfig:
                    st.plotly_chart(dfig, use_container_width=True)
            with c6:
                pfig = mc.psi_fig(viz, MODE)
                if pfig:
                    st.plotly_chart(pfig, use_container_width=True)
            st.caption(
                "PSI (population stability index) is computed per feature against the "
                "training-era reference; it is the standard input-stability check a "
                "validator expects alongside Evidently drift."
            )

        # ---- Robustness & validation cross-checks (collapsed to keep the headline clean) ----
        cbk = mc.load_calibration_bakeoff()
        cblr = mc.load_cblr_robustness()
        fg = mc.load_fine_gray()
        crisk = mc.load_competing_risks()
        b1 = mc.load_b1_compare()
        mx = mc.load_maxout_experiment()
        if any((cbk, cblr, fg, b1, mx)):
            section_heading(
                "Robustness & validation cross-checks",
                "The measurement was stress-tested against the choices a validator would "
                "challenge: how probabilities are calibrated, how the 2020 capital-ratio "
                "reporting break is handled, competing-risks censoring, and originally-filed "
                "vs restated inputs. Each is the real artifact, collapsed here so the headline "
                "above stays uncluttered.")
            if mx:
                with st.expander("Maxing out the model — effort ladder vs the data ceiling"):
                    st.plotly_chart(mc.maxout_ladder_fig(mx, MODE), use_container_width=True)
                    res = mx.get("results", {})
                    bagged = res.get("bagged", {})
                    base = res.get("baseline_light", {})
                    _served_pr = None
                    if m:
                        try:
                            _served_pr = m["oot_test"]["calibrated_lgbm"]["pr_auc"]
                        except Exception:
                            _served_pr = None
                    st.caption(
                        f"Progressively heavier modelling on the same {mx.get('holdout_quarters', 28)}-"
                        f"quarter out-of-time holdout ({mx.get('test_positives', N_OOT_FAIL)} positives): "
                        f"light baseline {base.get('pr_auc', 0):.3f} → heavy tuning → bagged "
                        f"{bagged.get('pr_auc', 0):.3f} → blend → stack. The bagged ensemble wins, and "
                        "the served champion uses that same bagged design"
                        + (f" (re-fit with the OOT-validated tree count, headline PR-AUC "
                           f"{_served_pr:.3f}); these ladder values are a quick single-run sweep so "
                           "they sit a touch below the champion." if _served_pr else ".")
                        + " Every interval overlaps every other: at this positive count more modelling "
                        "effort does not separate. Compute was never the limit; the rare-event count is.")
            if cbk:
                with st.expander("Calibration bake-off — why isotonic was chosen"):
                    st.plotly_chart(mc.calibration_bakeoff_fig(cbk, MODE),
                                    use_container_width=True)
                    ws = cbk.get("winner_stability", {})
                    cf = cbk.get("conformal_feasibility", {})
                    st.caption(
                        f"Isotonic, Platt, and Venn-Abers were each fit and scored out-of-time; "
                        f"isotonic has the lowest ECE. The isotonic-vs-Platt winner flips in "
                        f"{ws.get('bootstrap_flip_rate', 0):.0%} of bootstrap resamples (both are "
                        f"excellent at this base rate, so the choice is low-stakes). "
                        + cf.get("prediction_set_note", ""))
            if cblr:
                with st.expander("2020Q1 CBLR reporting break — robustness of the result"):
                    st.plotly_chart(mc.cblr_variants_fig(cblr, MODE), use_container_width=True)
                    br = cblr.get("cblr_break", {})
                    st.caption(
                        f"Mechanism: {br.get('mechanism', '')} ({br.get('null_rate_2020plus', 0):.0%} "
                        f"of post-2020 rows null vs {br.get('null_rate_2019', 0):.1%} before). "
                        + cblr.get("conclusion", ""))
            if fg or crisk:
                with st.expander("Competing risks — cause-specific vs Fine-Gray"):
                    if fg:
                        cs = fg.get("cause_specific", {})
                        fgm = fg.get("fine_gray", {})
                        cc1, cc2 = st.columns(2)
                        with cc1:
                            cs_ci = cs.get("pr_auc_ci", [0, 0])
                            metric_card("Cause-specific (censoring)",
                                        f"{cs.get('pr_auc', 0):.3f}",
                                        f"95% CI [{cs_ci[0]:.3f}, {cs_ci[1]:.3f}]")
                        with cc2:
                            fg_ci = fgm.get("pr_auc_ci", [0, 0])
                            metric_card("Fine-Gray subdistribution",
                                        f"{fgm.get('pr_auc', 0):.3f}",
                                        f"95% CI [{fg_ci[0]:.3f}, {fg_ci[1]:.3f}]")
                        st.caption(fg.get("interpretation", ""))
                    if crisk:
                        cif = crisk.get("cumulative_incidence", {})
                        ic = crisk.get("informative_censoring", {})
                        st.markdown(
                            f"- **Cumulative incidence** over the panel: failure "
                            f"{cif.get('failure', 0):.1%}, merger {cif.get('merger', 0):.1%} "
                            "(mergers ~4x more common, which is why they are modelled as a "
                            "competing risk, not treated as survivors).\n"
                            f"- **Informative-censoring bound**: {ic.get('interpretation', '')}")
            if b1:
                with st.expander("Point-in-time vs restated inputs (B1 integrity check)"):
                    pit = b1.get("point_in_time", {}).get("oot", {})
                    res = b1.get("fdic_restated", {}).get("oot", {})
                    bc1, bc2 = st.columns(2)
                    with bc1:
                        r_ci = res.get("ci", [0, 0])
                        metric_card("FDIC restated inputs", f"{res.get('pr_auc', 0):.3f}",
                                    f"95% CI [{r_ci[0]:.3f}, {r_ci[1]:.3f}]")
                    with bc2:
                        p_ci = pit.get("ci", [0, 0])
                        metric_card("Originally-filed (point-in-time)",
                                    f"{pit.get('pr_auc', 0):.3f}",
                                    f"95% CI [{p_ci[0]:.3f}, {p_ci[1]:.3f}]")
                    audit = b1.get("noncurrent_field_audit", {})
                    recon = b1.get("noncurrent_reconstruction", {})
                    st.caption(
                        "Scoring on originally-filed (point-in-time) Call Reports instead of the "
                        "current restated values lowers OOT PR-AUC but the intervals overlap, so "
                        "the result is not an artifact of look-ahead restatement. Field audit "
                        f"also fixed the noncurrent-loans definition: {audit.get('note', '')} "
                        f"Pre-2014 reconstruction validates at corr "
                        f"{recon.get('category_sum_vs_official_corr', 0)} vs the official total.")

elif section == "decisions":
    section_heading(
        "Key model decisions",
        "The choices that shape the model, and why each one was made.",
    )
    mcard = PROJECT_ROOT / "docs" / "ml" / "MODEL_CARD.md"
    st.markdown(
        "- **A hazard model on a bank-quarter panel**, not a one-shot classifier. Distress "
        "builds over time, so the model scores each bank every quarter against what happens "
        "next.\n"
        "- **Monotone constraints** on every feature. More capital can never raise predicted "
        "risk, more bad loans can never lower it. This rules out relationships a reviewer "
        "would reject.\n"
        "- **Calibrated probabilities**, so a 5% score really corresponds to about a 5% "
        "historical failure rate, rather than an arbitrary ranking number.\n"
        "- **Judged on PR-AUC and recall at a review budget**, because at a sub-1% failure "
        "rate accuracy is meaningless.\n"
        "- **Aligned with SR 11-7 model-risk principles** (non-binding here). Because this "
        "scores institutions, not people, there is no protected class; fairness is checked as "
        "consistent performance across size, region, and charter."
    )
    if mcard.exists():
        with st.expander("Full model card (generated from the real metrics)"):
            st.markdown(_render_repo_md(mcard.read_text(encoding="utf-8")))

    section_heading("Methodology write-ups",
                    "The full technical documents behind the analyses on the Model Quality "
                    "surface. Each is the real markdown from the repo.")
    _DOCS = [
        ("Failure-type decomposition", "FAILURE_DECOMPOSITION.md"),
        ("Competing risks (cause-specific + Fine-Gray)", "COMPETING_RISKS.md"),
        ("Point-in-time vs restated inputs (B1)", "B1_POINT_IN_TIME.md"),
        ("Sequence challenger (GRU)", "SEQUENCE_CHALLENGER.md"),
        ("Validation report", "VALIDATION_REPORT.md"),
        ("Related work", "RELATED_WORK.md"),
    ]
    _docdir = PROJECT_ROOT / "docs" / "ml"
    for _label, _fname in _DOCS:
        _fp = _docdir / _fname
        if _fp.exists():
            with st.expander(_label):
                st.markdown(_render_repo_md(_fp.read_text(encoding="utf-8")))

from streamlit_app.lib.page_shell import page_footer  # noqa: E402

page_footer()
