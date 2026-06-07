# ruff: noqa: E402
"""Predictive Analytics, REAL interactive bank-distress scoring.

Backed by the trained model (ml/finlens_ml). Three in-page tabs (st.tabs = no full
reload): insert a real bank by CERT, hold out a real failed bank (predicted vs
actual), and a hypothetical what-if with CAMELS sliders. Every number is computed
live from the calibrated model + SHAP.
"""

import sys
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

from finlens_ml.features import FEATURE_COLUMNS
from streamlit_app.lib import ml_charts as mc
from streamlit_app.lib.page_shell import BUSINESS_PAGE, page_intro, status_ribbon, top_navigation
from streamlit_app.lib.telemetry import record_page_view
from streamlit_app.lib.theme import app_css, ensure_theme_state, get_theme_mode
from streamlit_app.lib.ui_components import chart_note, inject_styles, section_heading

st.set_page_config(
    page_title="FinLens | Early Warning", layout="wide", initial_sidebar_state="collapsed"
)
ensure_theme_state()
inject_styles(app_css(get_theme_mode(), sidebar_open=True))
top_navigation("predictive", BUSINESS_PAGE)
record_page_view("predictive_analytics", BUSINESS_PAGE)
MODE = get_theme_mode()


@st.cache_resource(show_spinner=False)
def _backend():
    import finlens_ml.scenario as scenario

    return scenario


def _model_available() -> bool:
    return (PROJECT_ROOT / "ml" / "artifacts" / "calibrated_h4.skops").exists() or (
        PROJECT_ROOT / "ml" / "artifacts" / "booster_h4.txt"
    ).exists()


def _tier(prob: float, threshold: float) -> tuple[str, str]:
    if prob >= threshold:
        return "HIGH RISK", "danger"
    if prob >= threshold / 2:
        return "ELEVATED", "warn"
    return "LOW RISK", "ok"


def _render_score(result: dict, actual: int | None = None, key: str = "score") -> None:
    prob = result["probability"]
    thr = result["threshold"]
    tier, cls = _tier(prob, thr)
    g, info = st.columns([1, 1.15], vertical_alignment="center")
    with g:
        st.plotly_chart(mc.probability_gauge(prob, thr, MODE), use_container_width=True,
                        key=f"ew_gauge_{key}")
    with info:
        st.markdown(
            f'<div class="ew-badge ew-{cls}">{tier}</div>'
            f'<div class="ew-sub">Calibrated probability of financial distress within four '
            f'quarters. Review threshold is {thr * 100:.0f}%: at or above it, the bank is '
            f'flagged for a closer look.</div>',
            unsafe_allow_html=True,
        )
        if actual is not None:
            ao = "FAILED" if actual == 1 else "Survived"
            aocls = "danger" if actual == 1 else "ok"
            st.markdown(
                f'<div class="ew-actual">What actually happened: '
                f'<span class="ew-pill ew-{aocls}">{ao}</span></div>',
                unsafe_allow_html=True,
            )
    reasons = pd.DataFrame(result["reasons"])
    if not reasons.empty:
        reasons["impact"] = reasons["shap"].abs().round(3)

        def _fmt_value(v: object) -> str:
            if v is None or (isinstance(v, float) and v != v):
                return "n/a (not reported)"
            if isinstance(v, (int, float)):
                return f"{v:,.3f}"
            return str(v)

        reasons["Driver"] = reasons["feature"].astype(str).map(scenario.humanize_feature)
        reasons["Reported value"] = reasons["value"].map(_fmt_value)
        reasons["Effect on this score"] = reasons["direction"].map(
            {"increases risk": "↑ pushed score up", "decreases risk": "↓ pushed score down"}
        ).fillna(reasons["direction"])
        reasons = reasons.rename(columns={"impact": "Weight"})
        section_heading(
            "Why this score",
            "How each factor moved THIS bank's score (its SHAP contribution). A low value on "
            "a 'capital lowers risk' feature still pushes the score up. Higher weight = "
            "larger influence.",
        )
        st.dataframe(
            reasons[["Driver", "Reported value", "Effect on this score", "Weight"]],
            hide_index=True,
            use_container_width=True,
        )


status_ribbon("Historical backtest + experimental live scoring")
page_intro(
    "Business Surface",
    "Early Warning",
    "Pick a bank and the model scores its distress probability and the factors behind it. "
    "Most tabs are a historical backtest (scored on past quarters whose outcome is already "
    "known, so the prediction can be checked against reality); the 'Live forward score' tab "
    "estimates a live bank's latest filing. A live score is a model estimate, not a forecast "
    "that a bank will fail, and failure is rare (base rate under 1%).",
    wiki_slug="how-to-read-a-stress-score",
)
st.markdown(
    '<div class="ew-flow">'
    f'<span class="ew-flow-step"><b>1. Inputs</b><br>{len(FEATURE_COLUMNS)} CAMELS-style '
    'Call Report ratios for the chosen bank-quarter</span>'
    '<span class="ew-flow-arrow">&rarr;</span>'
    '<span class="ew-flow-step"><b>2. Model</b><br>calibrated, monotone-constrained '
    'gradient-boosted hazard model</span>'
    '<span class="ew-flow-arrow">&rarr;</span>'
    '<span class="ew-flow-step"><b>3. Output</b><br>a probability, a colour-coded risk '
    'tier, and the SHAP drivers behind it</span>'
    '</div>',
    unsafe_allow_html=True,
)

if not _model_available():
    chart_note(
        "Model artifact not present",
        "Train the model (python ml/finlens_ml/train.py) to activate this surface.",
    )
    st.stop()

scenario = _backend()
tab_insert, tab_holdout, tab_live, tab_what_if = st.tabs(
    ["Backtest any bank (by name)", "Failed-bank backtests",
     "Live forward score (experimental)", "Hypothetical what-if"]
)

with tab_insert:
    st.write(
        "Pick a U.S. bank and the model scores it **as of a past quarter whose outcome is "
        "already known**, then compares its prediction to what actually happened. This is a "
        "historical check of the model, not a forecast: forward-looking scoring is "
        "deliberately turned off."
    )
    directory = scenario.bank_directory()
    labels = directory["label"].tolist()
    default_idx = next(
        (i for i, lbl in enumerate(labels) if lbl.startswith("INDYMAC")), 0
    )
    choice = st.selectbox(
        "Bank",
        labels,
        index=default_idx,
        key="insert_bank_pick",
        help="Type to search. Only banks with a known, elapsed outcome are listed.",
        placeholder="Start typing a bank name…",
    )
    if choice:
        pick = directory[directory["label"] == choice].iloc[0]
        row = scenario.latest_known_row_for_cert(int(pick["cert"]))
        if row is None:
            st.warning("That bank has no quarter with a known outcome to backtest.")
        else:
            st.success(
                f"{row['bank_name']} ({row['state']}), scored as of {row['quarter']} "
                f"(outcome known) · FDIC CERT {row['cert']}"
            )
            _render_score(scenario.score_features(row["features"]), row["actual_label_4"], key="insert")

with tab_holdout:
    st.write(
        "Pick a bank that **actually failed**. The model scores a quarter ahead of the "
        "failure so you can compare its distress probability against the real, known outcome."
    )
    failed = scenario.held_out_failed_banks(limit=25)
    if failed.empty:
        st.info("No labeled failures in the panel.")
    else:
        failed["label"] = failed["bank_name"] + " (" + failed["state"].fillna("?") + ", " + failed["quarter"] + ")"
        choice = st.selectbox("Failed bank", failed["label"].tolist(), key="holdout_pick")
        pick = failed[failed["label"] == choice].iloc[0]
        row = scenario.latest_known_row_for_cert(int(pick["cert"]))
        if row is not None:
            _render_score(scenario.score_features(row["features"]), row["actual_label_4"], key="holdout")

with tab_live:
    chart_note(
        "Read this before you read the number",
        "This is a MODEL ESTIMATE on a live bank's most recent public filing, not a "
        "forecast that the bank will fail. Bank failure is rare (base rate under 1%), so "
        "even a relatively high score means the bank is very probably fine. The number is "
        "a calibrated probability from a backtested model, not advice, not a rating, and "
        "not a basis for any deposit, investment, or business decision. For decisions "
        "about a bank, rely only on official U.S. regulator sources.",
    )
    import json as _json
    try:
        _served_pr = _json.loads(
            (PROJECT_ROOT / "ml" / "artifacts" / "metrics_h4.json").read_text()
        )["oot_test"]["calibrated_lgbm"]["pr_auc"]
        _pr_txt = f"~{_served_pr:.2f}"
    except Exception:
        _pr_txt = "~0.30"
    _nfail = (mc.load_panel_facts() or {}).get("oot_failures", 66)
    st.write(
        "Score a live U.S. bank as of its **latest available quarter**, whose 4-quarter "
        f"outcome has not yet elapsed. The model's out-of-time track record (PR-AUC {_pr_txt} "
        f"on {_nfail} real failures, with wide intervals) is on the AI Engineering surface; treat "
        "this as a screening estimate, nothing more."
    )
    live = scenario.live_bank_directory()
    llabels = live["label"].tolist()
    lchoice = st.selectbox(
        "Bank (live)", llabels, key="live_bank_pick",
        help="Type to search. Scores the most recent available filing.",
        placeholder="Start typing a bank name…",
    )
    if lchoice:
        lpick = live[live["label"] == lchoice].iloc[0]
        lrow = scenario.latest_row_for_cert(int(lpick["cert"]))
        if lrow is None:
            st.warning("No data for that bank.")
        else:
            tag = ("outcome already known" if lrow["outcome_known"]
                   else "FORWARD estimate — outcome not yet elapsed")
            st.info(
                f"{lrow['bank_name']} ({lrow['state']}), scored as of {lrow['quarter']} "
                f"· FDIC CERT {lrow['cert']} · {tag}"
            )
            _render_score(
                scenario.score_features(lrow["features"]),
                lrow["actual_label_4"], key="live",
            )

with tab_what_if:
    st.write(
        "Move the CAMELS levers to build a hypothetical bank and watch the live score. "
        "Levers you don't touch are set to the typical (median) bank, so the score "
        "reflects a complete, realistic institution."
    )
    vals = {}
    cols = st.columns(3)
    for i, (feat, (lo, hi, default)) in enumerate(scenario.SLIDER_FEATURES.items()):
        with cols[i % 3]:
            vals[feat] = st.slider(
                scenario.SLIDER_LABELS.get(feat, feat),
                float(lo), float(hi), float(default), key=f"wi_{feat}",
            )
    _render_score(scenario.score_hypothetical(vals), key="whatif")
    st.caption(
        "This is a made-up bank, not a real institution. Monotone constraints are enforced: "
        "more capital never increases predicted risk; higher noncurrent loans never decreases it."
    )

chart_note(
    "Please read this",
    "Most tabs here are a historical backtest on public FDIC data (scored on past quarters "
    "whose outcome has already elapsed, so the prediction can be checked against reality). "
    "The 'Live forward score' tab additionally estimates a probability for a live bank's "
    "latest filing; that is a MODEL ESTIMATE, not a forecast that a bank will fail. Bank "
    "failure is rare (base rate under 1%), so even an elevated score almost always resolves "
    "to survival. Nothing here is financial, investment, deposit, or supervisory advice, or "
    "a rating; for decisions about a bank rely only on official U.S. government and "
    "regulator sources.",
)


from streamlit_app.lib.page_shell import page_footer  # noqa: E402

page_footer()
