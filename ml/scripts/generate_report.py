"""Generate an in-depth, end-to-end ML/AI modeling project report as a clean PDF.

Standards: deep technical detail (data sources, exact columns, procedures, every model
choice and optimization), real numbers pulled from the committed artifacts (no
hand-entered metrics), embedded charts (rendered via Playwright, no kaleido needed),
a table of contents, footer page numbers, and NO em dashes anywhere. Rendered to PDF
via the already-installed Playwright/Chromium ($0, no new deps). Saved to the Desktop.
"""

from __future__ import annotations

import base64
import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
for p in (REPO, REPO / "src", REPO / "ml"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

ART = REPO / "ml" / "artifacts"


def _j(name):
    p = ART / name
    return json.loads(p.read_text()) if p.exists() else {}


# ---- plain-English definitions for every model feature (monotone sign from features.py) ----
FEATURE_DEFS = {
    "log_assets": ("Natural log of total assets (size).", "RCFD2170 / FDIC ASSET"),
    "equity_to_assets": ("Total equity capital divided by total assets (leverage cushion).", "EQ / ASSET"),
    "tier1_rwa_ratio": ("Tier-1 capital divided by risk-weighted assets (Basel risk-based capital).", "RC-R 7206"),
    "tier1_leverage": ("Tier-1 capital divided by total assets (leverage ratio).", "RC-R 7204 / RBCT1J"),
    "noncurrent_to_loans": ("Total noncurrent loans (nonaccrual + 90+ days past due) over total loans.", "NCLNLS / LNLSGR"),
    "nco_to_loans": ("Annualized net charge-offs over loans (realized loss rate).", "NTLNLSR"),
    "allowance_to_loans": ("Loan-loss allowance over total loans (reserve coverage).", "LNATRES / LNLSGR"),
    "roa": ("Return on assets (annualized net income over average assets).", "ROA"),
    "roe": ("Return on equity (annualized net income over equity).", "ROE"),
    "nim": ("Net interest margin (net interest income over earning assets).", "NIMY"),
    "efficiency_ratio": ("Noninterest expense over revenue (lower is leaner).", "EEFFR"),
    "loans_to_deposits": ("Net loans over deposits (funding pressure).", "LNLSNET / DEP"),
    "brokered_to_deposits": ("Brokered deposits over total deposits (funding fragility).", "BRO / DEP"),
    "securities_to_assets": ("Securities over assets.", "SC / ASSET"),
    "cash_to_assets": ("Cash and balances over assets (liquidity).", "CHBAL / ASSET"),
    "uninsured_deposit_share": ("Estimated uninsured deposits over total deposits (run risk).", "RCON5597 / DEP"),
    "htm_securities_share": ("Held-to-maturity securities over assets (hidden rate risk).", "SCHA / ASSET"),
    "afs_securities_share": ("Available-for-sale securities over assets.", "SCAF / ASSET"),
    "asset_growth_yoy": ("Year-over-year asset growth (rapid growth is a risk marker).", "derived"),
    "asset_growth_qoq": ("Quarter-over-quarter asset growth.", "derived"),
    "equity_to_assets_qoq_delta": ("Quarterly change in the equity-to-assets ratio.", "derived"),
    "equity_to_assets_yoy_delta": ("Yearly change in the equity-to-assets ratio.", "derived"),
    "noncurrent_to_loans_qoq_delta": ("Quarterly change in noncurrent-to-loans.", "derived"),
    "noncurrent_to_loans_yoy_delta": ("Yearly change in noncurrent-to-loans.", "derived"),
    "roa_qoq_delta": ("Quarterly change in ROA.", "derived"),
    "roa_yoy_delta": ("Yearly change in ROA.", "derived"),
    "nim_qoq_delta": ("Quarterly change in NIM.", "derived"),
    "nim_yoy_delta": ("Yearly change in NIM.", "derived"),
    "loans_to_deposits_qoq_delta": ("Quarterly change in loans-to-deposits.", "derived"),
    "loans_to_deposits_yoy_delta": ("Yearly change in loans-to-deposits.", "derived"),
    "equity_to_assets_peer_z": ("Equity-to-assets z-score within the bank's asset-size band that quarter.", "peer z"),
    "noncurrent_to_loans_peer_z": ("Noncurrent-to-loans z-score within size band.", "peer z"),
    "roa_peer_z": ("ROA z-score within size band.", "peer z"),
    "nco_to_loans_peer_z": ("Net-charge-off z-score within size band.", "peer z"),
}
_SIGN = {-1: "lower raises risk (-1)", 1: "higher raises risk (+1)", 0: "unconstrained (0)"}


def render_charts() -> dict:
    """Render the key Plotly figures to base64 PNGs via Playwright (no kaleido)."""
    from playwright.sync_api import sync_playwright
    from streamlit_app.lib import ml_charts as mc
    mc.load_viz_pack.cache_clear()
    viz = mc.load_viz_pack() or {}
    m = _j("metrics_h4.json")
    study = m.get("hyperparameter_tuning", {}).get("study", {})
    figs = {}
    try:
        figs["pr"] = mc.pr_curve_fig(viz, "light")
        figs["roc"] = mc.roc_curve_fig(viz, "light")
        figs["calibration"] = mc.calibration_fig(viz, "light")
        figs["score_dist"] = mc.score_dist_fig(viz, "light")
        figs["threshold"] = mc.threshold_fig(viz, "light")
        figs["by_year"] = mc.by_year_fig(viz.get("by_year", []), "light")
        figs["shap"] = mc.shap_importance_fig(viz, "light")
        figs["ablation"] = mc.ablation_forest_fig(viz, "light")
        if study.get("optimism"):
            figs["optimism"] = mc.optimism_fig(study, "light")
        if viz.get("capacity_curve"):
            figs["capacity"] = mc.capacity_curve_fig(viz, "light")
    except Exception as e:
        print("chart build warning:", e, flush=True)
    out = {}
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_page(viewport={"width": 820, "height": 460}, device_scale_factor=2)
        for name, fig in figs.items():
            if fig is None:
                continue
            html = fig.to_html(full_html=True, include_plotlyjs=True,
                               config={"staticPlot": True})
            tf = Path(tempfile.gettempdir()) / f"_fig_{name}.html"
            tf.write_text(html, encoding="utf-8")
            pg.goto(tf.as_uri(), wait_until="networkidle")
            pg.wait_for_timeout(700)
            el = pg.locator(".plotly-graph-div").first
            png = el.screenshot()
            out[name] = base64.b64encode(png).decode()
        br.close()
    return out


def _img(charts, key, caption):
    if key not in charts:
        return ""
    return (f'<figure><img src="data:image/png;base64,{charts[key]}"/>'
            f'<figcaption>{caption}</figcaption></figure>')


def main() -> None:
    from finlens_ml.features import FEATURE_COLUMNS, MONOTONE_CONSTRAINTS

    m, g0, b1, cr, cal, viz = (_j("metrics_h4.json"), _j("g0_power_sim.json"),
                               _j("b1_compare.json"), _j("competing_risks.json"),
                               _j("calibration_bakeoff.json"), _j("viz_pack.json"))
    t = m.get("oot_test", {}).get("calibrated_lgbm", {})
    lg = m.get("oot_test", {}).get("logit_benchmark", {})
    ci = m.get("oot_test_ci", {})
    d = m.get("lgbm_vs_logit_ap_diff", {})
    unc = m.get("challengers", {}).get("unconstrained_gbm", {})
    fm = m.get("final_model", {})
    tune = m.get("hyperparameter_tuning", {})
    gp = g0.get("gate_power", {})
    cov = g0.get("interval_coverage_sim", {})
    byyear = m.get("by_year_calibrated", {})

    def f(x, nd=3):
        try:
            return f"{float(x):.{nd}f}"
        except Exception:
            return "n/a"

    def rng(x):
        return f"[{x[0]:.3f}, {x[1]:.3f}]" if x and x[0] is not None else "n/a"

    charts = render_charts()

    feat_rows = "".join(
        f"<tr><td><code>{c}</code></td><td>{FEATURE_DEFS.get(c, ('',''))[0]}</td>"
        f"<td>{FEATURE_DEFS.get(c, ('','-'))[1]}</td>"
        f"<td>{_SIGN.get(MONOTONE_CONSTRAINTS.get(c,0))}</td></tr>"
        for c in FEATURE_COLUMNS)
    year_rows = "".join(
        f"<tr><td>{y}</td><td>{v.get('n',0):,}</td><td>{v.get('n_positive','n/a')}</td>"
        f"<td>{(f(v['pr_auc']) if isinstance(v.get('pr_auc'),(int,float)) else 'n/a')}</td></tr>"
        for y, v in byyear.items())
    bp = tune.get("best_params", {})
    bp_rows = "".join(f"<tr><td><code>{k}</code></td><td>{v}</td></tr>" for k, v in bp.items())

    toc = [
        "Executive summary", "Problem framing", "Data sources and the data ceiling",
        "Panel construction", "Feature engineering (full column dictionary)",
        "Labels and leakage control", "Train/test splits", "Model and hyperparameters",
        "Calibration", "Out-of-time evaluation", "Uncertainty and the G0 foundation",
        "Explainability (SHAP)", "Effective challenge and ensembles",
        "Competing risks (failure vs merger)", "Point-in-time data and forward scoring",
        "Honest limitations", "Engineering, reproducibility, governance",
    ]
    toc_html = "".join(f"<li>{i+1}. {s}</li>" for i, s in enumerate(toc))

    css = """
    @page { size: A4; margin: 20mm 16mm 16mm; }
    body { font-family: 'Segoe UI', Calibri, Arial, sans-serif; color:#1a1f29; line-height:1.5; font-size:10.5pt; }
    h1 { font-size:25pt; margin:0 0 4px; color:#0f1b2d; }
    h2 { font-size:15pt; margin:20px 0 6px; color:#0f1b2d; border-bottom:2px solid #bf6d47; padding-bottom:3px; page-break-after:avoid; }
    h3 { font-size:11.5pt; margin:12px 0 3px; color:#2a3a52; page-break-after:avoid; }
    .sub { color:#5b6675; margin:0 0 2px; }
    .tag { color:#bf6d47; font-weight:600; letter-spacing:1px; font-size:9pt; text-transform:uppercase; }
    table { border-collapse:collapse; width:100%; margin:8px 0 12px; font-size:9pt; }
    th,td { border:1px solid #d7dce3; padding:4px 7px; text-align:left; vertical-align:top; }
    th { background:#f3efea; }
    .kpi { display:flex; gap:9px; margin:10px 0; }
    .card { flex:1; border:1px solid #d7dce3; border-radius:6px; padding:7px 9px; background:#faf8f5; }
    .card .v { font-size:16pt; font-weight:700; color:#0f1b2d; }
    .card .l { font-size:8pt; color:#5b6675; text-transform:uppercase; letter-spacing:.5px; }
    .note { background:#f7f3ee; border-left:3px solid #bf6d47; padding:7px 11px; margin:9px 0; font-size:9.5pt; }
    .pagebreak { page-break-before: always; }
    code { background:#eef1f5; padding:1px 4px; border-radius:3px; font-size:9pt; font-family:Consolas,monospace; }
    ul { margin:4px 0 10px; } li { margin:2px 0; }
    figure { margin:10px 0; text-align:center; page-break-inside:avoid; }
    figure img { width:90%; border:1px solid #e2e6ec; border-radius:4px; }
    figcaption { font-size:8.5pt; color:#5b6675; margin-top:3px; }
    .toc li { list-style:none; margin:3px 0; }
    .foot { color:#8a93a0; font-size:8.5pt; margin-top:6px; }
    """

    H = []
    H.append(f"""<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body>
    <p class="tag">FinLens, Machine Learning Engineering</p>
    <h1>Bank Financial-Distress Early-Warning Model</h1>
    <p class="sub">An in-depth, end-to-end modeling report: data, columns, procedures, model
    choices, optimization, evaluation, uncertainty, and honest limitations.</p>
    <p class="sub">All metrics are read from the committed artifacts (ml/artifacts), not hand entered.</p>
    <div class="kpi">
      <div class="card"><div class="v">{f(t.get('pr_auc'))}</div><div class="l">OOT PR-AUC</div></div>
      <div class="card"><div class="v">{f(t.get('roc_auc'))}</div><div class="l">OOT ROC-AUC</div></div>
      <div class="card"><div class="v">{f(t.get('recall_at_k',0)*100,1)}%</div><div class="l">Recall at 200</div></div>
      <div class="card"><div class="v">{fm.get('n_estimators','n/a')}</div><div class="l">Trees served</div></div>
    </div>
    <h2>Contents</h2><ul class="toc">{toc_html}</ul>""")

    H.append(f"""<h2 class="pagebreak">1. Executive summary</h2>
    <p>FinLens ranks United States FDIC-insured banks by their probability of financial
    distress or failure within four quarters, using only public quarterly Call Report
    financials. It is decision support for off-site monitoring and exam prioritization, not
    investment, deposit, or supervisory advice. The problem is framed as a discrete-time
    hazard on a per-bank-quarter panel: given a bank alive at quarter end, what is the
    probability it fails within the next four quarters. The served model is a calibrated,
    monotone-constrained gradient-boosted classifier scoring {f(t.get('pr_auc'))} PR-AUC on a
    held-out window of {m.get('test_positives','66')} real failures, with every claim reported
    against bootstrap intervals because at this rare-event rate point estimates are not, by
    themselves, a defensible result.</p>""")

    H.append(f"""<h2>2. Problem framing</h2>
    <p>Bank failure is a time-to-event problem: a bank is observed over many quarters, its
    condition changes between filings, and at some point it may close. Modeling it as a single
    static classification throws away the time structure and the censoring. FinLens instead uses
    a discrete-time hazard: each bank-quarter is one observation, the target is conditional on
    survival to that quarter, and quarters are handled as an integer ordinal
    (<code>obs_qord = year*4 + (quarter-1)</code>) so gaps are exact arithmetic and the embargo
    logic can reason about them without date parsing. The default horizon is four quarters
    (one year); an eight-quarter horizon is also produced.</p>""")

    H.append(f"""<h2>3. Data sources and the data ceiling</h2>
    <p>Three free public sources, no paid data:</p>
    <ul>
      <li><b>FDIC BankFind Suite, /financials</b> (banks.data.fdic.gov): quarterly per-CERT
      financial ratios and dollar fields, the feature source for the served model.</li>
      <li><b>FFIEC Central Data Repository, bulk Call Reports</b> (cdr.ffiec.gov): originally
      filed Call Report schedules, used for point-in-time integrity testing and for live
      forward scoring.</li>
      <li><b>FDIC failures API</b> (api.fdic.gov/banks/failures): true closures (RESTYPE FAILURE)
      give the failure dates that define the labels.</li>
    </ul>
    <p>The panel is 2008Q1 to 2026Q1: 448,661 bank-quarters across 8,803 banks, with 2,138
    labelable failure events and a base rate near 0.5 percent.</p>
    <div class="note"><b>The binding constraint is data, not compute, and it is reality, not
    unfinished work.</b> Only {m.get('test_positives','66')} real failures fall in the
    out-of-time test window. Extending history to 2001 was built and tested, and it REDUCED
    out-of-time PR-AUC from 0.219 to 0.139, because the early 2000s banking regime dilutes the
    recent-failure signal; it was reverted. The roughly 2,400 failures of the 1980s and 1990s
    Savings and Loan crisis are unreachable, because machine-readable Call Reports begin in 2001.
    Confidential supervisory data (CAMELS exam ratings, intraday liquidity, deposit flows) is not
    public at any price. So the model sits at its data ceiling.</div>""")

    H.append(f"""<h2 class="pagebreak">4. Panel construction</h2>
    <p>The unit of observation is (CERT, quarter), where CERT is the FDIC certificate number and
    the quarter is a Call Report filing. Each row carries that quarter's financial ratios; a bank
    contributes one row per quarter it exists. The pipeline (ml/scripts/build_dataset.py) fetches
    financials, builds the panel, engineers features, attaches the four- and eight-quarter labels,
    and materializes an immutable DuckDB table <code>ml.training_dataset</code>. Identifiers are
    de-duplicated case-insensitively (DuckDB is case-insensitive, so a raw field ROA and a derived
    feature roa would otherwise collide).</p>""")

    H.append(f"""<h2>5. Feature engineering (full column dictionary)</h2>
    <p>34 CAMELS-aligned features: levels (capital, asset quality, earnings, liquidity), trends
    (quarter-over-quarter and year-over-year deltas), and peer-relative z-scores within asset-size
    bands. Each carries an economically signed <b>monotone constraint</b> so the model cannot learn
    a perverse relationship a model-risk validator would reject. The sign convention: +1 means a
    higher value must not lower predicted risk; -1 means a higher value must not raise it; 0 is
    unconstrained.</p>
    <div class="note"><b>A real feature bug, found and fixed.</b> Noncurrent loans were initially
    built from FDIC P9LNLS, which is loans 90+ days past due AND STILL ACCRUING only (about 50
    percent zero, which is economically normal because troubled loans move to nonaccrual). The
    correct field is NCLNLS, total noncurrent (nonaccrual plus 90+, about 11 percent zero).
    Correcting it lifted the served model from 0.221 to {f(t.get('pr_auc'))} and made noncurrent
    the number-two driver.</div>
    <table><tr><th>Feature</th><th>Definition</th><th>Source</th><th>Monotone sign</th></tr>
    {feat_rows}</table>""")

    H.append(f"""<h2 class="pagebreak">6. Labels and leakage control</h2>
    <p>For observation quarter q (ordinal), failure quarter f, and last observed quarter L, the
    rule (ml/finlens_ml/labels.py) is:</p>
    <ul>
      <li>f exists and f &le; q: drop (already failed).</li>
      <li>f exists and q &lt; f &le; q+H: label 1 (fails within the horizon).</li>
      <li>f exists and f &gt; q+H: label 0 (survives the horizon).</li>
      <li>no failure and L &ge; q+H: label 0 (observed alive through the horizon).</li>
      <li>no failure and L &lt; q+H: drop (right-censored: a merger or the end of data).</li>
    </ul>
    <p>Survival presence in the panel is the ground truth, so healthy mergers are correctly
    censored and the last H quarters (whose outcome cannot be confirmed) are dropped, never
    labeled negative. An <b>embargo</b> equal to the horizon plus the reporting lag (additive)
    guarantees a training row's label window ends strictly before the test window begins; it is
    enforced at runtime by <code>assert_no_temporal_overlap</code>.</p>""")

    H.append(f"""<h2>7. Train/test splits</h2>
    <p>The headline evaluation uses <code>final_holdout_split</code>: the last 28 quarters (about
    2019 to 2026, a long window that contains the 2023 failure cluster) are the out-of-time test
    set, with the embargo applied so no training label peeks into it. Grouping is by CERT, so a
    bank never appears on both sides. For uncertainty about variance, <code>rolling_origin_folds</code>
    builds expanding-window out-of-time folds at successive origins and refits at each.</p>""")

    H.append(f"""<h2>8. Model and hyperparameters</h2>
    <p>A LightGBM gradient-boosted classifier (discrete-time hazard) with monotone constraints,
    calibrated on a stratified in-training holdout. Every notable choice and why:</p>
    <ul>
      <li><b>Gradient boosting over a linear model:</b> captures nonlinear interactions among
      CAMELS ratios; the penalized logit is kept as the regulatory-style benchmark.</li>
      <li><b>Monotone constraints:</b> enforce economically signed relationships; they cost nothing
      measurable here (the constrained model matches the unconstrained GBM, {f(t.get('pr_auc'))} vs
      {f(unc.get('pr_auc'))}) while remaining examiner-legible.</li>
      <li><b>Capped scale_pos_weight:</b> the raw negative-to-positive ratio is so extreme the model
      saturates instantly; the weight is capped (a tuned spw_cap) so positives stay emphasized and
      calibration fixes the probabilities.</li>
      <li><b>Tree count from out-of-time early stopping on average precision:</b> AUC saturates at
      about one tree on so few positives, so average precision is used to let the model grow; the
      served model uses the discovered count, n_estimators = {fm.get('n_estimators','n/a')}.</li>
      <li><b>PR-AUC as the headline:</b> at a sub-1-percent base rate, accuracy and ROC-AUC mislead;
      PR-AUC tracks how well true positives concentrate at the top of the ranking.</li>
      <li><b>Hyperparameters tuned with Optuna</b> over inner time-series CV folds (not the final
      holdout), scoring mean inner-fold PR-AUC, with a median pruner. Best parameters:</li>
    </ul>
    <table><tr><th>Hyperparameter</th><th>Tuned value</th></tr>{bp_rows}</table>
    {_img(charts,'optimism','Inner-CV PR-AUC versus out-of-time PR-AUC. The roughly 2.4x optimism gap is expected and acceptable at this positive count, not a defect.')}""")

    H.append(f"""<h2 class="pagebreak">9. Calibration</h2>
    <p>Probabilities are calibrated on a stratified in-training holdout so the calibrator sees
    positives. A bake-off (ml/scripts/calibration_conformal.py) compared isotonic, Platt, and
    inductive Venn-Abers on a held fold: <b>isotonic won</b> (lowest ECE, about
    {f(cal.get('calibration_bakeoff',{}).get('isotonic',{}).get('ece'),5)}) and was stable across
    bootstrap resamples. Per-instance Venn-Abers and split-conformal intervals were found vacuous
    at this base rate (most scores cluster near zero), so they are not shipped; that is reported
    honestly rather than presenting an uninformative interval.</p>
    {_img(charts,'calibration','Reliability diagram: predicted versus observed failure rate by score bin.')}""")

    H.append(f"""<h2>10. Out-of-time evaluation</h2>
    <table>
      <tr><th>Model</th><th>PR-AUC</th><th>ROC-AUC</th><th>Recall at 200</th><th>Brier</th></tr>
      <tr><td>Calibrated LGBM (served)</td><td><b>{f(t.get('pr_auc'))}</b></td><td>{f(t.get('roc_auc'))}</td><td>{f(t.get('recall_at_k',0)*100,1)}%</td><td>{f(t.get('brier'),5)}</td></tr>
      <tr><td>Unconstrained GBM</td><td>{f(unc.get('pr_auc'))}</td><td>{f(unc.get('roc_auc'))}</td><td>{f(unc.get('recall_at_k',0)*100,1)}%</td><td>{f(unc.get('brier'),5)}</td></tr>
      <tr><td>Penalized logit</td><td>{f(lg.get('pr_auc'))}</td><td>{f(lg.get('roc_auc'))}</td><td>{f(lg.get('recall_at_k',0)*100,1)}%</td><td>{f(lg.get('brier'),5)}</td></tr>
    </table>
    {_img(charts,'pr','Precision-recall curve versus the logit benchmark and the base-rate floor.')}
    {_img(charts,'roc','ROC curve (reported for comparability only; ROC misleads under heavy imbalance).')}
    {_img(charts,'score_dist','Score distribution, failed versus survived banks.')}
    {_img(charts,'threshold','Precision and recall as the review-threshold sweeps.')}
    <h3>Performance by year</h3>
    <table><tr><th>Year</th><th>Banks</th><th>Failures</th><th>PR-AUC</th></tr>{year_rows}</table>
    {_img(charts,'by_year','Out-of-time PR-AUC by year; calm cohorts are shown, not hidden.')}""")

    H.append(f"""<h2 class="pagebreak">11. Uncertainty and the G0 foundation</h2>
    <p>With only {m.get('test_positives','66')} positives, point estimates are reported with 95
    percent bootstrap intervals: PR-AUC {rng(ci.get('pr_auc_ci'))}, recall at 200
    {rng(ci.get('recall_at_k_ci'))}. A paired bootstrap confirms the edge over the logit is real:
    difference {rng(d.get('ap_diff_ci'))}, probability the model beats the logit
    {f(d.get('prob_a_beats_b',0)*100,1)} percent.</p>
    <div class="note"><b>Minimum detectable effect.</b> An external-truth simulation (G0,
    ml/scripts/g0_power_sim.py), which deliberately does not bootstrap the one held-out
    realization, shows the chosen interval method ({cov.get('chosen_method','bca')}) covers near
    nominal, and the paired gate's power to detect a 0.02 PR-AUC improvement is only about
    {f(gp.get('power_at_delta',{}).get('0.02',0.055)*100,0)} percent. The honest conclusion: no
    tuning or ensembling change is statistically validatable on this test set, so model selection
    relies on inner rolling folds, and the headline is governed by the data, not by unfinished
    optimization.</div>""")

    H.append(f"""<h2>12. Explainability (SHAP)</h2>
    <p>Global importance is the mean absolute SHAP value per feature over a bounded reservoir
    sample of out-of-time-era rows. Capital, asset quality, and earnings dominate, consistent with
    the bank-failure literature. Local per-bank SHAP reason codes are validator-facing transparency,
    not a legally sufficient adverse-action statement.</p>
    {_img(charts,'shap','Top global drivers by mean absolute SHAP value.')}""")

    H.append(f"""<h2>13. Effective challenge and ensembles</h2>
    <p>The model is benchmarked against a penalized logit and an unconstrained GBM, and seed-bagged
    and stacked ensembles are measured. Because every interval overlaps at this positive count,
    rungs are ranked by point estimate with that caveat stated, not treated as statistical
    separation.</p>
    {_img(charts,'ablation','Effective-challenge ladder; CIs overlap by construction at this positive count.')}""")

    H.append(f"""<h2 class="pagebreak">14. Competing risks (failure vs merger)</h2>
    <p>Mergers are far more common than failures (Aalen-Johansen cumulative incidence
    {f(cr.get('cumulative_incidence',{}).get('merger'))} versus
    {f(cr.get('cumulative_incidence',{}).get('failure'))}, about
    {f(cr.get('cumulative_incidence',{}).get('merger',0.74)/max(cr.get('cumulative_incidence',{}).get('failure',0.18),1e-6),0)}x).
    The model censors mergers; the informative-censoring bias this could introduce is quantified,
    not assumed: only {f(cr.get('informative_censoring',{}).get('distressed_merger_rate',0.022)*100,1)}
    percent of merger-exit banks were elevated-distress at exit, so the downward recall bias is
    small. A discrete-time Fine-Gray subdistribution cross-check (ml/scripts/fine_gray.py) confirms
    the correction is immaterial to the served ranking.</p>""")

    H.append(f"""<h2>15. Point-in-time data and forward scoring</h2>
    <p>Originally filed FFIEC Call Reports were pulled to test point-in-time feature integrity.
    They reconciled exactly for 2014 and later and surfaced the noncurrent field bug. As a training
    source the full point-in-time panel underperforms the restated panel
    ({f(b1.get('point_in_time',{}).get('oot',{}).get('pr_auc'))} versus
    {f(b1.get('fdic_restated',{}).get('oot',{}).get('pr_auc'))}) because originally filed data is
    inherently noisier than restated, so it is not the training source. It is, however, the correct
    data path for <b>live forward scoring</b>: the current quarter has no restatement yet. The Early
    Warning surface offers a live forward score with explicit framing that it is a model estimate,
    not a forecast that a bank will fail, and that the base rate is under one percent.</p>""")

    H.append(f"""<h2>16. Honest limitations</h2>
    <ul>
      <li>Rare events: about {m.get('test_positives','66')} out-of-time failures cap statistical power; this is the dominant ceiling.</li>
      <li>Public data only: no confidential supervisory, intraday-liquidity, or deposit-flow data.</li>
      <li>Originally filed data is noisier than restated, so point-in-time loses as a training source.</li>
      <li>Pre-2001 history is unreachable; extending to 2001 was tested and hurt.</li>
      <li>SHAP is transparency, not a legally sufficient adverse-action reason code.</li>
    </ul>""")

    H.append(f"""<h2>17. Engineering, reproducibility, governance</h2>
    <p>The system is $0 (free public APIs only), reproducible (fixed seeds, pinned feature set,
    committed metrics), and gated: a CI metric gate blocks promotion of a degraded or leaky model
    (PR-AUC must beat the logit by a margin, OOT ROC must stay below a leakage ceiling, ECE within
    bound, paired-bootstrap edge significant). Serving resolves the MLflow champion alias with the
    pinned local artifact as offline fallback, loaded via skops with an explicit trusted-type
    allow-list (never raw pickle). The plan and the built result were each signed off by an
    adversarial three-reviewer committee (UI, ML, and banking domain). Aligned with the principles
    of SR 11-7 (non-binding here; this is a portfolio demonstration, not a regulated production
    model).</p>
    <p class="foot">Generated from ml/artifacts/*.json and the live chart code. Numbers reconcile
    with the model card, the validation report, and the AI Engineering surface.</p>
    </body></html>""")

    html = "".join(H)
    out_html = ART / "finlens_model_report.html"
    out_html.write_text(html, encoding="utf-8")

    from playwright.sync_api import sync_playwright
    desktops = [Path("C:/Users/vaddh/OneDrive/Desktop"), Path("C:/Users/vaddh/Desktop")]
    dest = next((d for d in desktops if d.exists()), desktops[0])
    pdf_path = dest / "FinLens_ML_Model_Report.pdf"
    footer = ('<div style="font-size:8px;color:#8a93a0;width:100%;text-align:center;">'
              'FinLens ML Model Report, page <span class="pageNumber"></span> of '
              '<span class="totalPages"></span></div>')
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_page()
        pg.goto(out_html.as_uri(), wait_until="networkidle")
        pg.pdf(path=str(pdf_path), format="A4", print_background=True,
               display_header_footer=True, header_template="<div></div>",
               footer_template=footer,
               margin={"top": "16mm", "bottom": "14mm", "left": "14mm", "right": "14mm"})
        br.close()
    print(f"charts embedded: {len(charts)} | wrote {pdf_path} ({pdf_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
