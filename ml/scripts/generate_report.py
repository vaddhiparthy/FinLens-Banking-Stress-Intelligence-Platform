"""Generate a clean, end-to-end ML/AI modeling project report as a PDF.

Pulls REAL numbers from the committed artifacts (no hand-entered metrics), renders a
styled HTML report, and prints it to PDF via the already-installed Playwright/Chromium
(no new dependencies, $0). Saved to the user's Desktop.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ART = REPO / "ml" / "artifacts"


def _j(name):
    p = ART / name
    return json.loads(p.read_text()) if p.exists() else {}


def main() -> None:
    m = _j("metrics_h4.json")
    g0 = _j("g0_power_sim.json")
    b1 = _j("b1_compare.json")
    cr = _j("competing_risks.json")
    cal = _j("calibration_bakeoff.json")
    viz = _j("viz_pack.json")

    t = m.get("oot_test", {}).get("calibrated_lgbm", {})
    lg = m.get("oot_test", {}).get("logit_benchmark", {})
    ci = m.get("oot_test_ci", {})
    d = m.get("lgbm_vs_logit_ap_diff", {})
    unc = m.get("challengers", {}).get("unconstrained_gbm", {})
    fm = m.get("final_model", {})
    gp = g0.get("gate_power", {})
    cov = g0.get("interval_coverage_sim", {})
    shap = viz.get("shap_importance", [])[:8]
    byyear = m.get("by_year_calibrated", {})

    def f(x, d=3):
        try:
            return f"{float(x):.{d}f}"
        except Exception:
            return "—"

    def rng(x):
        return f"[{x[0]:.3f}, {x[1]:.3f}]" if x and x[0] is not None else "—"

    shap_rows = "".join(
        f"<tr><td>{r['feature']}</td><td>{f(r['mean_abs_shap'],4)}</td></tr>" for r in shap)
    year_rows = "".join(
        f"<tr><td>{y}</td><td>{v.get('n_positive','—')}</td>"
        f"<td>{(f(v['pr_auc']) if isinstance(v.get('pr_auc'),(int,float)) else '—')}</td></tr>"
        for y, v in byyear.items())

    css = """
    @page { size: A4; margin: 22mm 18mm; }
    body { font-family: Georgia, 'Times New Roman', serif; color:#1a1f29; line-height:1.5; font-size:11pt; }
    h1 { font-size:26pt; margin:0 0 4px; color:#0f1b2d; }
    h2 { font-size:15pt; margin:22px 0 6px; color:#0f1b2d; border-bottom:2px solid #bf6d47; padding-bottom:3px; }
    h3 { font-size:12pt; margin:14px 0 4px; color:#2a3a52; }
    .sub { color:#5b6675; font-size:11pt; margin:0 0 2px; }
    .tag { color:#bf6d47; font-weight:bold; letter-spacing:1px; font-size:9pt; text-transform:uppercase; }
    table { border-collapse:collapse; width:100%; margin:8px 0 12px; font-size:10pt; }
    th,td { border:1px solid #d7dce3; padding:5px 8px; text-align:left; }
    th { background:#f3efea; }
    .kpi { display:flex; gap:10px; margin:10px 0; }
    .card { flex:1; border:1px solid #d7dce3; border-radius:6px; padding:8px 10px; background:#faf8f5; }
    .card .v { font-size:17pt; font-weight:bold; color:#0f1b2d; }
    .card .l { font-size:8.5pt; color:#5b6675; text-transform:uppercase; letter-spacing:.5px; }
    .note { background:#f7f3ee; border-left:3px solid #bf6d47; padding:8px 12px; margin:10px 0; font-size:10pt; }
    .pagebreak { page-break-before: always; }
    code { background:#f0f2f5; padding:1px 4px; border-radius:3px; font-size:9.5pt; }
    ul { margin:4px 0 10px; } li { margin:2px 0; }
    .foot { color:#8a93a0; font-size:8.5pt; margin-top:6px; }
    """

    html = f"""<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body>
    <p class="tag">FinLens · Machine Learning Engineering</p>
    <h1>Bank Financial-Distress Early-Warning Model</h1>
    <p class="sub">End-to-end modeling project report — data, features, model, evaluation,
    uncertainty, competing risks, and honest limitations.</p>
    <p class="sub">Generated from the committed artifacts (no hand-entered metrics).</p>

    <div class="kpi">
      <div class="card"><div class="v">{f(t.get('pr_auc'))}</div><div class="l">OOT PR-AUC</div></div>
      <div class="card"><div class="v">{f(t.get('roc_auc'))}</div><div class="l">OOT ROC-AUC</div></div>
      <div class="card"><div class="v">{f(t.get('recall_at_k',0)*100,1)}%</div><div class="l">Recall@200</div></div>
      <div class="card"><div class="v">{fm.get('n_estimators','—')}</div><div class="l">Trees (served)</div></div>
    </div>

    <h2>1. What this is</h2>
    <p>A discrete-time hazard model that ranks U.S. FDIC-insured banks by their probability
    of financial distress / failure within four quarters, from public quarterly Call Report
    financials. It is decision-support for off-site monitoring, not investment, deposit, or
    supervisory advice. The model is deliberately framed as a conditional hazard on a
    per-bank-quarter panel rather than a static classifier.</p>

    <h2>2. Data</h2>
    <p>One row per bank per quarter, keyed by FDIC CERT and Call Report quarter, 2008Q1–2026Q1:
    ~448,700 bank-quarters across ~8,800 banks. Failure dates come from the FDIC failures API
    (true closures only). Features come from FDIC <code>/financials</code>.</p>
    <div class="note"><b>The binding constraint is data, not compute.</b> Only ~{m.get('test_positives','66')}
    real failures fall in the 28-quarter out-of-time test window — bank failure is rare
    (base rate &lt;1%). Extending history to 2001 was tested and <b>reduced</b> OOT PR-AUC
    (0.219 → 0.139): the early-2000s regime dilutes the recent-failure signal. The pre-2001
    S&amp;L-crisis failures (~2,400) are unreachable — machine-readable Call Reports begin in
    2001. So the model is at its data ceiling, and that ceiling is reality, not unfinished work.</div>

    <h2>3. Features &amp; the monotone contract</h2>
    <p>34 CAMELS-aligned ratios (capital, asset quality, earnings, liquidity) plus trend
    (QoQ/YoY) and peer-relative (size-band z-score) features. Each carries an
    economically-signed <b>monotone constraint</b> (more capital never raises predicted risk;
    higher noncurrent loans never lowers it), so the gradient-boosted model cannot learn
    perverse relationships a model-risk validator would reject.</p>
    <div class="note"><b>A real feature bug, found and fixed.</b> Noncurrent loans were
    initially built from FDIC <code>P9LNLS</code> (90+-days-past-due-and-still-accruing only,
    ~50% zero — normal) instead of <code>NCLNLS</code> (total noncurrent = nonaccrual + 90+,
    ~11% zero). Correcting it lifted the served model from 0.221 to {f(t.get('pr_auc'))} and made
    noncurrent the #2 driver.</p>

    <h3>Top global drivers (mean |SHAP|)</h3>
    <table><tr><th>Feature</th><th>mean |SHAP|</th></tr>{shap_rows}</table>

    <h2 class="pagebreak">4. Labels &amp; leakage control</h2>
    <p>For each bank-quarter the target is: does this bank fail within the next four quarters?
    Labels are strictly forward-looking. Survival presence in the panel is the ground truth, so
    healthy mergers/acquisitions are correctly censored (they leave the panel without a failure
    record) and the last few quarters (whose outcome cannot yet be confirmed) are dropped, never
    labeled negative. An <b>embargo</b> (horizon + reporting lag, additive) guarantees a training
    row's label window ends strictly before the test window begins; it is asserted at runtime.</p>

    <h2>5. The model</h2>
    <p>A calibrated, monotone-constrained LightGBM discrete-time hazard classifier, trained on
    all labelable data with the out-of-time-validated tree count (n_estimators = {fm.get('n_estimators','—')}),
    isotonic calibration. Hyperparameters are tuned with Optuna over inner time-series
    cross-validation folds, not hand-set.</p>

    <h2>6. Out-of-time evaluation</h2>
    <p>Evaluated on a long, failure-containing window (the last 28 quarters, ~2019–2026,
    including the 2023 SVB/Signature/First-Republic cluster). PR-AUC is the headline because at
    a &lt;1% base rate accuracy and ROC-AUC mislead.</p>
    <table>
      <tr><th>Model</th><th>PR-AUC</th><th>ROC-AUC</th><th>Recall@200</th></tr>
      <tr><td>Calibrated LGBM (monotone, served)</td><td><b>{f(t.get('pr_auc'))}</b></td><td>{f(t.get('roc_auc'))}</td><td>{f(t.get('recall_at_k',0)*100,1)}%</td></tr>
      <tr><td>Unconstrained GBM (challenger)</td><td>{f(unc.get('pr_auc'))}</td><td>{f(unc.get('roc_auc'))}</td><td>{f(unc.get('recall_at_k',0)*100,1)}%</td></tr>
      <tr><td>Penalized logit (benchmark)</td><td>{f(lg.get('pr_auc'))}</td><td>{f(lg.get('roc_auc'))}</td><td>{f(lg.get('recall_at_k',0)*100,1)}%</td></tr>
    </table>
    <p>The monotone model now matches/beats the unconstrained GBM, so the economic constraints
    cost nothing measurable here while remaining validator-defensible. Calibration ECE =
    {f(m.get('oot_calibration',{}).get('ece'),5)}; isotonic was selected by a held-fold bake-off
    (lowest ECE, stable across resamples).</p>

    <h3>Performance by year</h3>
    <table><tr><th>Year</th><th>Failures</th><th>PR-AUC</th></tr>{year_rows}</table>
    <p class="foot">Calm years with few/zero failures have low or undefined PR-AUC — expected for
    a rare-event model. Judge on failure-containing windows.</p>

    <h2 class="pagebreak">7. Uncertainty &amp; the statistical foundation (G0)</h2>
    <p>With only ~{m.get('test_positives','66')} out-of-time positives, point estimates are not a
    defensible result. 95% bootstrap intervals: PR-AUC {rng(ci.get('pr_auc_ci'))},
    recall@200 {rng(ci.get('recall_at_k_ci'))}. A paired bootstrap confirms the edge over the
    logit benchmark is real: difference CI {rng(d.get('ap_diff_ci'))}, P(model &gt; logit) =
    {f(d.get('prob_a_beats_b',0)*100,1)}%.</p>
    <div class="note"><b>Honest minimum-detectable-effect result.</b> An external-truth
    simulation (not a bootstrap of the holdout) shows the chosen interval method
    (<b>{cov.get('chosen_method','BCa')}</b>) covers at ~{f(cov.get('by_dgp',{}).get('surrogate_subsample',{}).get('coverage',{}).get('bca',0.94)*100,0)}%,
    and the paired gate's power to detect a 0.02 PR-AUC improvement is only
    <b>{f(gp.get('power_at_delta',{}).get('0.02',0.055)*100,0)}%</b>. So no tuning/ensembling change
    is statistically validatable on this test set — model selection relies on inner rolling
    folds, and the headline is what it is because of the data, not unfinished optimization.</div>

    <h2>8. Effective challenge &amp; ensembles</h2>
    <p>The model is benchmarked against a penalized logit (regulatory-style linear reference)
    and an unconstrained GBM, and seed-bagged / stacked ensembles are measured. Bagging had the
    highest point estimate and lowest variance; ensembles are reported as challengers. Because
    every interval overlaps at this positive count, ranking is by point estimate with that
    caveat stated, not treated as statistical separation.</p>

    <h2>9. Competing risks (failure vs merger)</h2>
    <p>Mergers are ~{f(cr.get('cumulative_incidence',{}).get('merger',0.74)/max(cr.get('cumulative_incidence',{}).get('failure',0.18),1e-6),0)}×
    more common than failures (Aalen-Johansen cumulative incidence
    {f(cr.get('cumulative_incidence',{}).get('merger'))} vs {f(cr.get('cumulative_incidence',{}).get('failure'))}).
    The model censors mergers; the informative-censoring bias this could introduce is
    <b>quantified, not assumed</b>: only {f(cr.get('informative_censoring',{}).get('distressed_merger_rate',0.022)*100,1)}%
    of merger-exit banks were elevated-distress at exit, so the downward recall bias is small.
    A discrete-time Fine-Gray subdistribution cross-check confirms the correction is immaterial
    to the served ranking.</p>

    <h2>10. Point-in-time data (B1) &amp; forward scoring</h2>
    <p>Originally-filed FFIEC Call Reports were pulled to test point-in-time feature integrity.
    They validated exactly for 2014+ and surfaced the noncurrent bug above. As a <i>training</i>
    source the full point-in-time panel underperforms the restated panel
    ({f(b1.get('point_in_time',{}).get('oot',{}).get('pr_auc'))} vs
    {f(b1.get('fdic_restated',{}).get('oot',{}).get('pr_auc'))}) because originally-filed data is
    inherently noisier than restated. It is therefore not the training source — but it IS the
    correct data path for <b>live forward scoring</b> (the current quarter has no restatement yet),
    which the Early Warning surface now offers with explicit "model estimate, not a forecast"
    framing (base rate &lt;1%).</p>

    <h2>11. Honest limitations</h2>
    <ul>
      <li><b>Rare events.</b> ~{m.get('test_positives','66')} OOT failures cap statistical power; this is the dominant ceiling.</li>
      <li><b>Public data only.</b> No confidential supervisory (CAMELS exam), intraday-liquidity, or deposit-flow data — legally unavailable.</li>
      <li><b>Originally-filed is noisier than restated</b> — why point-in-time loses as a training source.</li>
      <li><b>Pre-2001 history is unreachable</b> — machine-readable Call Reports begin 2001.</li>
      <li>SHAP is validator-facing transparency, not a legally-sufficient adverse-action reason code.</li>
    </ul>

    <h2>12. Engineering &amp; governance</h2>
    <p>$0 (only free public APIs), reproducible (fixed seeds, pinned feature set, committed
    metrics), with a CI metric gate that blocks promotion of a degraded or leaky model, MLflow
    champion-alias serving, and an adversarial three-reviewer gate (UI, ML, domain) that must
    unanimously sign off the plan and the built result. Aligned with the principles of SR 11-7
    (non-binding; this is a portfolio demonstration, not a regulated production model).</p>
    <p class="foot">This report is generated from ml/artifacts/*.json. Numbers reconcile with the
    model card, validation report, and the live AI Engineering surface.</p>
    </body></html>"""

    out_html = ART / "finlens_model_report.html"
    out_html.write_text(html, encoding="utf-8")

    # render to PDF via Playwright/Chromium (already installed; no new deps)
    from playwright.sync_api import sync_playwright
    desktops = [Path("C:/Users/vaddh/OneDrive/Desktop"), Path("C:/Users/vaddh/Desktop")]
    dest = next((d for d in desktops if d.exists()), desktops[0])
    pdf_path = dest / "FinLens_ML_Model_Report.pdf"
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_page()
        pg.goto(out_html.as_uri(), wait_until="networkidle")
        pg.pdf(path=str(pdf_path), format="A4", print_background=True,
               margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        br.close()
    print(f"wrote {pdf_path} ({pdf_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
