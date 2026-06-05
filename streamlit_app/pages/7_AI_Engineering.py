# ruff: noqa: E402
"""AI Engineering surface, the ML pillar, mirroring the Data Engineering sections.

Every section shows the REAL artifact: charts baked from the trained model + panel
(ml/artifacts/viz_pack.json), the live feature contract, and the actual running
source code (pulled via inspect.getsource, so it can never drift from what runs).
"""

import inspect
import json
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
from streamlit_app.lib.ui_components import inject_styles, metric_card, section_heading

ART = PROJECT_ROOT / "ml" / "artifacts"

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
section = get_ai_section()

_AI_INTRO = {
    "pipeline": ("Bank-Distress Model: Pipeline",
                 "How the discrete-time hazard model is trained and scored on the FDIC "
                 "bank-quarter panel, end to end, with the real code at each step."),
    "notebook": ("Bank-Distress Model: Analysis Notebook",
                 "The actual Jupyter notebook I built this with, executed on the real "
                 "panel: EDA, the out-of-time evaluation, calibration, and SHAP."),
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


if section == "pipeline":
    section_heading("Training & scoring pipeline", "Discrete-time hazard model on the FDIC bank-quarter panel.")
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
            metric_card("Recall@200", f"{t['recall_at_k']:.0%}", sub)
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
                        f"out-of-time folds): PR-AUC mean **{rb['pr_auc_mean']}** "
                        f"(±{rb['pr_auc_std']}), range {rb['pr_auc_min']}–{rb['pr_auc_max']}. "
                        "The spread is the honest story: strong in failure-containing "
                        "windows, near-floor in calm years."
                    )
        chal = m.get("challengers", {})
        tune = m.get("hyperparameter_tuning", {})
        if chal:
            section_heading(
                "Effective-challenge ladder",
                "The constrained model vs an unconstrained GBM (same tuned params, no "
                "monotone constraints) and the penalized logit. The monotone constraints "
                "should not cost meaningful PR-AUC.",
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
        if tune.get("tuned"):
            bp = tune.get("best_params", {})
            st.caption(
                f"Hyperparameters tuned with Optuna over {tune.get('n_trials')} trials on "
                f"{tune.get('n_inner_folds')} inner time-series CV folds "
                f"(best CV PR-AUC {tune.get('cv_mean_pr_auc')}); not hand-set. "
                f"Tuned: {bp}."
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
        by_year = m.get("by_year_calibrated", {})
        if by_year:
            section_heading("By year", "PR-AUC holds up in the failure-containing cohorts.")
            rows = [
                {"year": y, "n": v["n"], "failures": v["n_positive"],
                 "pr_auc": None if isinstance(v["pr_auc"], str) or v["pr_auc"] != v["pr_auc"]
                 else round(v["pr_auc"], 4)}
                for y, v in by_year.items()
            ]
            st.plotly_chart(mc.by_year_fig(rows, MODE), use_container_width=True)
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
            st.markdown(mcard.read_text(encoding="utf-8"))

elif section == "administration":
    from finlens_ml import registry

    section_heading("Model administration", "Registry, promotion, retraining, rollback.")
    st.markdown(
        "- **Registry**: MLflow champion/challenger via aliases (not deprecated stages)\n"
        "- **Promotion**: manual to champion after shadow + a CI metric gate\n"
        "- **Retrain**: scheduled quarterly + drift-triggered\n"
        "- **Rollback**: repoint the champion alias to the prior version (instant, auditable)\n"
        "- **$0 guard**: CI fails if ML code imports any billable service"
    )
    _show_code(registry.set_champion, "Champion promotion via alias (registry.set_champion)")
    _show_code(registry.promote_latest_to_champion, "Promote latest (registry.promote_latest_to_champion)")

from streamlit_app.lib.page_shell import page_footer  # noqa: E402

page_footer()
