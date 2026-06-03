"use strict";
/* FinLens console — hash-routed multi-surface SPA. Surfaces: Home, Business, Data
   Engineering, Machine Learning, Wiki, Architect's Desk. All data from baked JSON +
   live /predict. No framework, no build step. */
const $ = (s, r = document) => r.querySelector(s);
const J = (p) => fetch(p).then((r) => (r.ok ? r.json() : Promise.reject(r.status)));
const fmt = (n, d = 2) => (n == null || Number.isNaN(n) ? "—" : Number(n).toFixed(d));
const esc = (s) => String(s ?? "").replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
const ACCENT = "#539bf5", ACC2 = "#6cb6ff", WARN = "#c69026", DANGER = "#e5534b", OK = "#57ab5a", LINE = "#373e47", TXT = "#768390";
const axis = { axisLine: { lineStyle: { color: LINE } }, axisLabel: { color: TXT }, splitLine: { lineStyle: { color: LINE } } };
const grid = { left: 52, right: 22, top: 28, bottom: 40 };

let D = {}; // data cache
const _charts = new Set(); let _rb = false;
function chart(sel) { const node = typeof sel === "string" ? $(sel) : sel; const c = echarts.getInstanceByDom(node) || echarts.init(node, null, { renderer: "canvas" }); c.clear(); _charts.add(c); if (!_rb) { _rb = true; addEventListener("resize", () => _charts.forEach((x) => x.resize())); } return c; }

document.addEventListener("DOMContentLoaded", async () => {
  $("#stackChips").innerHTML = ["FDIC", "FRED", "DuckDB", "dbt", "Airflow", "LightGBM", "MLflow", "SHAP", "FastAPI", "Evidently", "ECharts"].map((t) => `<span class="chip">${t}</span>`).join("");
  pollApi(); setInterval(pollApi, 15000);
  try {
    const [meta, perf, banks, feats, timeline, biz, wiki, graph] = await Promise.all(
      ["meta", "performance", "banks", "features", "timeline", "business", "wiki", "architecture_graph"].map((n) => J(`/data/${n}.json`)));
    D = { meta, perf, banks, feats, timeline, biz, wiki, graph };
  } catch (e) { $("#view").innerHTML = `<div class="home"><div class="empty">Data failed to load (${e}). Run ml/scripts/export_web_data.py.</div></div>`; return; }
  addEventListener("hashchange", route); route();
});

async function pollApi() {
  const b = $("#apiBadge"), t = $("#apiText"), t0 = performance.now();
  try { const r = await J("/ready"); b.className = "api-badge online"; t.textContent = `model online · ${(r.model_version || "v").split("-").slice(-1)[0]} · ${Math.round(performance.now() - t0)}ms`; }
  catch { b.className = "api-badge offline"; t.textContent = "model offline"; }
}

/* ---------------- router ---------------- */
function route() {
  const parts = (location.hash.replace(/^#\/?/, "").split("/").filter(Boolean));
  const surface = parts[0] || "home";
  document.querySelectorAll(".surface-switch a").forEach((a) => a.classList.toggle("active", a.dataset.surface === surface));
  const v = $("#view"); v.scrollTo?.(0, 0);
  try {
    if (surface === "home" || surface === "") renderHome(v);
    else if (surface === "business") renderSurface(v, "business", BUSINESS, parts[1], renderBusiness);
    else if (surface === "de") renderSurface(v, "de", DE, parts[1], renderDE);
    else if (surface === "ml") renderSurface(v, "ml", ML, parts[1], renderML);
    else if (surface === "wiki") renderWiki(v, parts.slice(1).join("/"));
    else if (surface === "desk") renderDesk(v, parts);
    else renderHome(v);
  } catch (e) { v.innerHTML = `<div class="surface"><div></div><div class="empty">render error: ${esc(e.message || e)}</div></div>`; }
  setTimeout(() => document.querySelectorAll(".reveal").forEach((n, i) => setTimeout(() => n.classList.add("in"), i * 40)), 20);
}

const BUSINESS = [["pulse", "Stress Pulse"], ["failures", "Failure Forensics"], ["macro", "Macro Transmission"], ["knowledge", "Knowledge"]];
const DE = [["pipeline", "Live Pipeline"], ["contracts", "Source Contracts"], ["medallion", "Medallion Layers"], ["transforms", "Transforms"], ["quality", "Data Quality"], ["lineage", "Lineage"], ["browser", "Data Browser"], ["code", "Code"], ["stack", "Stack"], ["adrs", "Architecture Decisions"]];
const ML = [["overview", "Overview"], ["contracts", "Feature Contracts"], ["performance", "Performance"], ["calibration", "Calibration"], ["explain", "Explainability"], ["drift", "Drift"], ["governance", "Governance"], ["admin", "Administration"], ["lab", "Live Stress Lab"]];

function renderSurface(v, key, sections, section, fn) {
  section = sections.some((s) => s[0] === section) ? section : sections[0][0];
  const rail = sections.map(([id, label]) => `<a class="${id === section ? "active" : ""}" href="#/${key}/${id}">${label}</a>`).join("");
  v.innerHTML = `<div class="surface"><nav class="rail"><div class="rail-title">${key === "de" ? "Data Engineering" : key === "ml" ? "Machine Learning" : "Business"}</div>${rail}</nav><div class="panel" id="panel"></div></div>`;
  fn($("#panel"), section);
}
function head(crumb, title, desc, extra = "") {
  return `<div class="panel-head"><div><div class="crumb">${crumb}</div><h2>${title}</h2><p>${desc}</p></div>${extra}</div>`;
}

/* ---------------- Home ---------------- */
function renderHome(v) {
  const o = D.meta.oot;
  v.innerHTML = `<div class="home">
    <div class="crumb reveal">Banking Stress Intelligence Platform</div>
    <h1 class="reveal">Bank financial-distress early-warning,<br/><span class="accent">data engineering → machine learning, end to end.</span></h1>
    <p class="lede reveal">A production-shaped platform on public FDIC + FRED data: a medallion data pipeline, a calibrated gradient-boosted hazard model with live inference, and an architect's desk mapping the whole system. ${o.n_test.toLocaleString()} out-of-time bank-quarters · ${o.failures} real failures · PR-AUC ${o.pr_auc} vs ${o.logit_pr_auc} logit.</p>
    <div class="disclaimer reveal">Personal analytical project using public U.S. government data sources. Not financial advice, and not a substitute for official FDIC/Federal Reserve sources.</div>
    <div class="vert-cards">
      <a class="vert-card reveal" href="#/business"><div class="k">Vertical 01</div><h3>Business</h3><p>Industry stress, failure forensics, and macro transmission — the banking story in charts.</p><div class="s">${D.banks.length} failures analysed →</div></a>
      <a class="vert-card reveal" href="#/de"><div class="k">Vertical 02</div><h3>Data Engineering</h3><p>Ingestion, medallion layers, data quality, lineage, orchestration — the pipeline behind it.</p><div class="s">Bronze → Silver → Gold →</div></a>
      <a class="vert-card reveal" href="#/ml"><div class="k">Vertical 03</div><h3>Machine Learning</h3><p>The distress model: performance, calibration, SHAP, drift, governance, and a live stress lab.</p><div class="s">Try live inference →</div></a>
    </div>
    <div class="side-links reveal"><a href="#/wiki">📖 Wiki — in-depth theory</a><a href="#/desk">🗺 Architect's Desk — the system map</a></div>
  </div>`;
}

/* ---------------- Business ---------------- */
function lineChart(el, x, series) { chart(el).setOption({ grid, tooltip: { trigger: "axis" }, legend: { textStyle: { color: TXT }, top: 0 }, xAxis: { type: "category", data: x, ...axis, axisLabel: { color: TXT, interval: Math.ceil(x.length / 10) } }, yAxis: { type: "value", ...axis }, series }); }
function barChart(el, x, y, color = ACCENT, horiz = false) {
  const cat = { type: "category", data: x, ...axis }, val = { type: "value", ...axis };
  chart(el).setOption({ grid: horiz ? { ...grid, left: 120 } : grid, tooltip: { trigger: "axis" }, xAxis: horiz ? val : cat, yAxis: horiz ? cat : val, series: [{ type: "bar", data: y, itemStyle: { color }, label: { show: horiz, position: "right", color: TXT } }] });
}
function renderBusiness(p, sec) {
  if (sec === "pulse") {
    const t = D.biz.system_trends, x = t.map((d) => d.quarter);
    p.innerHTML = head("Business · Stress Pulse", "Industry Stress Pulse", "System-level banking health from the per-institution panel: median capital, earnings, and asset quality across all FDIC-insured banks each quarter.") +
      `<div class="grid g2"><div class="card"><div class="chart-label">Median ROA & capital ratio (%)</div><div id="c1" class="chart"></div></div><div class="card"><div class="chart-label">Median noncurrent loans & uninsured deposits (%)</div><div id="c2" class="chart"></div></div></div>`;
    lineChart("#c1", x, [{ name: "median ROA", type: "line", smooth: true, showSymbol: false, data: t.map((d) => d.med_roa), lineStyle: { color: ACCENT } }, { name: "median equity/assets", type: "line", smooth: true, showSymbol: false, data: t.map((d) => d.med_capital), lineStyle: { color: ACC2 } }]);
    lineChart("#c2", x, [{ name: "median noncurrent", type: "line", smooth: true, showSymbol: false, data: t.map((d) => d.med_noncurrent), lineStyle: { color: WARN } }, { name: "median uninsured", type: "line", smooth: true, showSymbol: false, data: t.map((d) => d.med_uninsured), lineStyle: { color: DANGER } }]);
  } else if (sec === "failures") {
    p.innerHTML = head("Business · Failure Forensics", "Failure Forensics", "Every FDIC bank failure in the panel window — when and where institutions failed.") +
      `<div class="grid g2"><div class="card"><div class="chart-label">Failures by quarter</div><div id="fq" class="chart"></div></div><div class="card"><div class="chart-label">Failures by year</div><div id="fy" class="chart"></div></div></div><div class="card" style="margin-top:16px"><div class="chart-label">Top states by failures</div><div id="fs" class="chart"></div></div>`;
    barChart("#fq", D.timeline.map((d) => d.quarter), D.timeline.map((d) => d.failures), ACCENT);
    barChart("#fy", D.biz.failures_by_year.map((d) => d.year), D.biz.failures_by_year.map((d) => d.failures), WARN);
    barChart("#fs", D.biz.failures_by_state.map((d) => d.state).reverse(), D.biz.failures_by_state.map((d) => d.failures).reverse(), ACC2, true);
  } else if (sec === "macro") {
    p.innerHTML = head("Business · Macro Transmission", "Macro Transmission", "The FRED macro series that feed the model's point-in-time context (as-released / ALFRED vintage, no look-ahead).") +
      `<div class="card"><table class="tbl"><thead><tr><th>Series</th><th>What it captures</th><th>Distress channel</th></tr></thead><tbody>
      ${[["UNRATE", "Unemployment rate", "credit losses"], ["DGS10–DGS2", "Term spread / inversion", "rate & NIM stress"], ["BAA10Y", "Corporate credit spread", "risk repricing"], ["NFCI", "Financial conditions index", "systemic stress"], ["CPIAUCSL", "Inflation", "real-rate context"]].map((r) => `<tr><td class="mono">${r[0]}</td><td>${r[1]}</td><td>${r[2]}</td></tr>`).join("")}
      </tbody></table><p class="subtle" style="margin-top:12px">Macro features are joined point-in-time using as-released vintages so the model never sees a revised value it could not have known at scoring time.</p></div>`;
  } else { // knowledge
    p.innerHTML = head("Business · Knowledge", "Business Knowledge", "Plain-language map of what the platform measures and why it matters to a banking audience.") +
      `<div class="grid g2">${[["What it is", "An early-warning system that ranks banks by financial-distress risk from their public Call Reports — the same data regulators monitor off-site."], ["Who it's for", "Risk, supervision, and executive reviewers who need to triage which institutions warrant attention, quarters ahead."], ["The signal", "Capital, asset quality, earnings, liquidity, and (post-2023) uninsured-deposit & securities-duration risk."], ["The honest limit", "Public data can't see confidential exam ratings; rate-driven runs like SVB are surfaced as elevated risk but not precisely timed."]].map((c) => `<div class="card reveal"><div class="section-title">${c[0]}</div><p class="muted">${c[1]}</p></div>`).join("")}</div>`;
  }
}

/* ---------------- Data Engineering ---------------- */
function deNodes(layer) { return D.graph.nodes.filter((n) => n.layer === layer || n.layer === "shared"); }
function renderDE(p, sec) {
  const deepLink = `<button class="deeplink" onclick="location.hash='#/desk/de'">Open DE Architecture →</button>`;
  if (sec === "pipeline") {
    const chain = ["fdic_src", "fred_src", "ingest", "bronze", "silver", "intermediate", "gold"].map((id) => D.graph.nodes.find((n) => n.id === id));
    p.innerHTML = head("Data Engineering · Live Pipeline", "Medallion Pipeline", "Source → bronze → silver → intermediate → gold, orchestrated by Airflow. Status reflects each component's implementation label.", deepLink) +
      `<div class="grid g4">${chain.map((n) => `<div class="stat reveal"><div class="v" style="font-size:1rem">${n.label}</div><div class="l">${n.prod_ref}</div><span class="pill ${n.status}">${n.status}</span></div>`).join("")}</div>
      <div class="card" style="margin-top:16px"><div class="section-title">Orchestration (Airflow DAGs)</div><table class="tbl"><thead><tr><th>DAG</th><th>Purpose</th><th>Schedule</th></tr></thead><tbody>
      ${[["dag_ingest_fdic/fred/qbp/nic", "source ingestion", "per source"], ["dag_transform_and_quality", "dbt build + GX checkpoints", "daily"], ["dag_ml_retrain", "quarterly model retrain + gate", "quarterly"], ["dag_sync_control_plane", "telemetry → Postgres", "daily"]].map((r) => `<tr><td class="mono">${r[0]}</td><td>${r[1]}</td><td>${r[2]}</td></tr>`).join("")}</tbody></table></div>`;
  } else if (sec === "contracts") {
    p.innerHTML = head("Data Engineering · Source Contracts", "Source Contracts", "Each ingested source, its cadence, landing layer, and downstream use.", deepLink) +
      `<div class="card"><table class="tbl"><thead><tr><th>Source</th><th>Cadence</th><th>Landing</th><th>Gold usage</th></tr></thead><tbody>
      ${[["FDIC institution financials", "Quarterly", "Bronze raw", "per-bank panel, features"], ["FDIC failed banks", "Periodic", "Bronze raw", "failure labels, forensics"], ["FRED / ALFRED macro", "Daily (vintage)", "Bronze obs", "macro context features"], ["NIC parent metadata", "Quarterly", "Bronze meta", "entity/parent context"]].map((r) => `<tr><td>${r[0]}</td><td>${r[1]}</td><td>${r[2]}</td><td>${r[3]}</td></tr>`).join("")}</tbody></table></div>`;
  } else if (sec === "medallion") {
    p.innerHTML = head("Data Engineering · Medallion", "Bronze / Silver / Gold", "Layered warehouse with dbt transforms; DuckDB locally, Snowflake DDL as the cloud target.", deepLink) +
      `<div class="grid g4">${[["Bronze", "Source fidelity (raw artifacts)"], ["Silver", "Canonical staging (dbt)"], ["Intermediate", "Reusable business logic (dbt)"], ["Gold", "Dashboard-ready marts (dbt)"]].map((l) => `<div class="card reveal"><div class="section-title">${l[0]}</div><p class="subtle">${l[1]}</p></div>`).join("")}</div>`;
  } else if (sec === "quality") {
    p.innerHTML = head("Data Engineering · Data Quality", "Data Quality Gates", "The quality gates defined in the pipeline (dbt tests, Great Expectations checkpoints, the CI model-metric gate, and the $0 import guard). These are real code paths in the repo; pass/fail counts are produced when the Airflow/CI run executes.", deepLink) +
      `<div class="card"><table class="tbl"><thead><tr><th>Gate</th><th>Tool</th><th>When</th><th>Defined in</th></tr></thead><tbody>
      ${[["schema / not-null / uniqueness", "dbt tests", "every build", "dbt/models/**/schema.yml"], ["distribution & freshness", "Great Expectations", "on-load / on-serve", "great_expectations/checkpoints/"], ["model metric gate (PR-AUC>logit, ROC<0.98, ECE)", "metric_gate.py", "CI + retrain DAG", "ml/scripts/metric_gate.py"], ["$0 import guard", "AST test", "every PR", "ml/tests/test_no_billable_imports.py"]].map((r) => `<tr><td>${r[0]}</td><td class="mono">${r[1]}</td><td>${r[2]}</td><td class="mono">${r[3]}</td></tr>`).join("")}</tbody></table></div>`;
  } else if (sec === "lineage") {
    p.innerHTML = head("Data Engineering · Lineage", "Pipeline Lineage", "Source-to-mart data flow (architecture model). The full end-to-end map including the ML path lives on the Architect's Desk.", deepLink) +
      `<div class="card"><div class="dag-wrap" id="lineageDag"></div></div>`;
    drawDag($("#lineageDag"), "de_lineage");
  } else if (sec === "stack") {
    p.innerHTML = head("Data Engineering · Stack", "Engineering Stack", "Production-grade patterns, free/OSS counterparts at $0.", deepLink) +
      `<div class="card"><table class="tbl"><thead><tr><th>Concern</th><th>Production tool</th><th>$0 counterpart</th></tr></thead><tbody>
      ${[["Ingestion", "Kafka + S3", "HTTP pull → local raw"], ["Transform", "Spark + dbt", "dbt on DuckDB"], ["Warehouse", "Snowflake", "DuckDB / Postgres"], ["Orchestration", "Airflow (managed)", "Airflow (self-host)"], ["Quality", "Soda / GX", "Great Expectations + dbt"], ["IaC", "Terraform", "Terraform (defined)"]].map((r) => `<tr><td>${r[0]}</td><td>${r[1]}</td><td class="mono">${r[2]}</td></tr>`).join("")}</tbody></table></div>`;
  } else if (sec === "transforms") {
    p.innerHTML = head("Data Engineering · Transforms", "Transformation Models (dbt)", "The dbt models that shape raw sources into gold marts, by layer.", deepLink) +
      `<div class="card"><table class="tbl"><thead><tr><th>Model</th><th>Layer</th><th>Does</th></tr></thead><tbody>
      ${[["stg_fdic_qbp / stg_fdic_failed_banks", "staging", "type + normalize raw FDIC"], ["stg_fred_observations", "staging", "normalize macro series"], ["int_failures_with_macro_context", "intermediate", "join failures + macro"], ["fct_stress_pulse", "mart", "system stress metrics"], ["fct_bank_failures", "mart", "failure forensics"], ["fct_financial_metrics", "mart", "macro indicators"], ["dim_date / dim_state", "reference", "conformed dimensions"]].map((r) => `<tr><td class="mono">${r[0]}</td><td>${r[1]}</td><td>${r[2]}</td></tr>`).join("")}</tbody></table></div>`;
  } else if (sec === "browser") {
    p.innerHTML = head("Data Engineering · Data Browser", "Data Browser", "Live rows from the gold bank-quarter panel (largest institutions, 2023+).", deepLink) + `<div class="card" id="browser"><div class="empty">loading…</div></div>`;
    J("/data/browser.json").then((bz) => {
      $("#browser").innerHTML = `<table class="tbl"><thead><tr>${bz.columns.map((c) => `<th>${c}</th>`).join("")}</tr></thead><tbody>${bz.rows.slice(0, 40).map((r) => `<tr>${r.map((v) => `<td>${typeof v === "number" ? (Number.isInteger(v) ? v.toLocaleString() : v.toFixed(2)) : esc(v)}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
    }).catch(() => { $("#browser").innerHTML = `<div class="empty">browser data not exported — run export_web_data.py</div>`; });
  } else if (sec === "code") {
    p.innerHTML = head("Data Engineering · Code", "Code Excerpts", "The real source paths behind each stage (open the repo to read the full code).", deepLink) +
      `<div class="card"><table class="tbl"><thead><tr><th>Stage</th><th>File</th></tr></thead><tbody>
      ${[["Ingestion", "ingestion/fdic_institutions.py"], ["Panel build", "ml/finlens_ml/data.py"], ["Features", "ml/finlens_ml/features.py"], ["dbt marts", "dbt/models/marts/"], ["Airflow DAG", "airflow/dags/dag_ml_retrain.py"], ["Serving", "ml/finlens_ml/serve.py"], ["Audit log", "ml/finlens_ml/audit.py"]].map((r) => `<tr><td>${r[0]}</td><td class="mono">${r[1]}</td></tr>`).join("")}</tbody></table></div>`;
  } else { // adrs
    p.innerHTML = head("Data Engineering · Architecture Decisions", "Architecture Decisions", "Key design choices, recorded as ADRs in the repo.", deepLink) +
      `<div class="grid g2">${[["Cloud object storage boundary", "Raw artifacts land before transform; S3 mirror optional and OFF for $0."], ["Kimball star schema", "Gold marts modelled dimensionally for analytics + serving."], ["SCD strategy", "Snapshots for slowly-changing dimensions."], ["Quality split (load vs serve)", "GX checkpoints at both ingestion and serving boundaries."]].map((c) => `<div class="card reveal"><div class="section-title">${c[0]}</div><p class="muted">${c[1]}</p></div>`).join("")}</div>`;
  }
}

/* ---------------- Machine Learning ---------------- */
function renderML(p, sec) {
  const deepLink = `<button class="deeplink" onclick="location.hash='#/desk/ml'">Open ML Architecture →</button>`;
  const o = D.meta.oot;
  if (sec === "overview") {
    p.innerHTML = head("Machine Learning · Overview", "Distress Model Overview", "A calibrated, monotone-constrained LightGBM discrete-time hazard model. Served champion resolved from the MLflow registry.", deepLink) +
      `<div class="grid g4">${[[`${o.pr_auc}`, "PR-AUC (out-of-time)", true], [`${(o.recall_at_k * 100).toFixed(0)}%`, `recall @ top ${o.k}`, true], [`${D.meta.n_features}`, "features", false], [`${D.meta.trees}`, "trees (served)", false]].map((s) => `<div class="stat reveal"><div class="v ${s[2] ? "good" : ""}">${s[0]}</div><div class="l">${s[1]}</div></div>`).join("")}</div>
      <div class="card" style="margin-top:16px"><div class="section-title">What it predicts</div><p class="muted">Probability that an institution enters financial distress / failure within ${D.meta.horizon_q} quarters, from public Call Report financials. Ranks banks for off-site supervisory triage — not investment, deposit, or supervisory advice.</p></div>`;
  } else if (sec === "contracts") {
    const mono = D.feats.monotone, dir = (v) => v > 0 ? "↑ raises risk" : v < 0 ? "↓ lowers risk" : "unconstrained";
    const rows = D.feats.features.map((f) => `<tr><td class="mono">${f}</td><td>${dir(mono[f])}</td></tr>`).join("");
    p.innerHTML = head("Machine Learning · Feature Contracts", `Feature Contract (${D.feats.features.length} features)`, "Every model feature and its economically-signed monotone direction vs. distress risk — enforced as a constraint in the model. Point-in-time: features lag the reporting cycle; labels are strictly forward-looking.", deepLink) +
      `<div class="card"><table class="tbl"><thead><tr><th>Feature</th><th>Monotone direction</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  } else if (sec === "admin") {
    const o2 = D.meta;
    p.innerHTML = head("Machine Learning · Administration", "Model Administration", "Registry, promotion, retraining, and rollback — the operational controls.", deepLink) +
      `<div class="grid g2">${[["Registry", `MLflow champion alias; serving resolves models:/finlens_bank_distress@champion (file fallback). Served: ${o2.trees} trees, ${o2.calibration} calibration.`], ["Promotion", "Manual to champion after the CI metric gate passes (PR-AUC>logit, ROC<0.98, ECE bound)."], ["Retraining", "Airflow dag_ml_retrain (quarterly + drift-triggered): build → train+register → gate → export."], ["Rollback", "Repoint the champion alias to the prior version — an instant, auditable serve-time rollback."], ["Audit", "Every served request logged (id, inputs, version, probability, reason codes) for outcomes analysis + prediction drift."], ["Cost", "$0 — CI import guard fails the build if ML code imports a billable service."]].map((c) => `<div class="card reveal"><div class="section-title">${c[0]}</div><p class="muted">${c[1]}</p></div>`).join("")}</div>`;
  } else if (sec === "performance") {
    p.innerHTML = head("Machine Learning · Performance", "Out-of-Time Performance", `PR-AUC is the headline at a ${o.base_rate_pct}% base rate; ROC-AUC is comparability-only.`, deepLink) +
      `<div class="grid g2"><div class="card"><div class="chart-label">Precision–Recall curve (logit benchmark PR-AUC ${o.logit_pr_auc})</div><div id="pr" class="chart"></div></div><div class="card"><div class="chart-label">ROC-AUC by year</div><div id="yr" class="chart"></div></div></div>`;
    chart($("#pr")).setOption({ grid, tooltip: { trigger: "axis" }, legend: { textStyle: { color: TXT }, top: 0 }, xAxis: { type: "value", name: "recall", min: 0, max: 1, ...axis }, yAxis: { type: "value", name: "precision", min: 0, max: 1, ...axis }, series: [{ name: `model ${o.pr_auc}`, type: "line", smooth: true, showSymbol: false, data: D.perf.pr_curve, lineStyle: { color: ACCENT, width: 2.5 }, areaStyle: { color: "rgba(45,212,191,.12)" } }] });
    const yrs = D.perf.by_year.filter((y) => y.roc_auc != null);
    barChart("#yr", yrs.map((y) => y.year), yrs.map((y) => ({ value: y.roc_auc, itemStyle: { color: y.roc_auc >= 0.8 ? ACCENT : WARN } })));
  } else if (sec === "calibration") {
    const c = o.ece;
    p.innerHTML = head("Machine Learning · Calibration", "Calibration", "Isotonic calibration; reported where decisions are made (top decile), since all-rows Brier is dominated by true negatives.", deepLink) +
      `<div class="grid g3">${[[`${c != null ? c.toExponential(1) : "—"}`, "Expected Calibration Error"], [`isotonic`, "method"], [`${D.meta.trees}`, "trees"]].map((s) => `<div class="stat reveal"><div class="v">${s[0]}</div><div class="l">${s[1]}</div></div>`).join("")}</div>
      <div class="card" style="margin-top:16px"><p class="muted">Served probabilities are calibrated: in the top-scoring decile the predicted and observed failure rates align closely, so a "5%" score means roughly a 5% failure rate.</p></div>`;
  } else if (sec === "explain") {
    p.innerHTML = head("Machine Learning · Explainability", "Global Drivers (SHAP)", "Mean |SHAP| over a sampled background. Capital and earnings dominate, consistent with the bank-failure literature; uninsured/HTM carry the 2023 rate-risk signal.", deepLink) +
      `<div class="card"><div class="chart-label">Model features — economic risk direction (amber = raises risk, teal = lowers risk)</div><div id="shap" class="chart"></div><p class="subtle" style="margin-top:8px">Monotone constraints enforce these directions in the model. Per-bank live SHAP reason codes are produced by the serving API — see the Live Stress Lab.</p></div>`;
    const items = Object.entries(D.feats.monotone).filter(([, v]) => v !== 0).slice(0, 14).reverse();
    chart($("#shap")).setOption({ grid: { ...grid, left: 180 }, tooltip: { show: false }, xAxis: { show: false, type: "value", max: 1 }, yAxis: { type: "category", data: items.map(([k]) => k), ...axis }, series: [{ type: "bar", barWidth: 12, data: items.map(([, v]) => ({ value: 1, itemStyle: { color: v > 0 ? WARN : ACCENT } })) }] });
  } else if (sec === "drift") {
    p.innerHTML = head("Machine Learning · Drift", "Drift Monitoring (Evidently)", "Data + prediction drift between the training era (2008–2018) and the current era (2019+). Prediction drift is the earliest signal since true failure labels arrive late.", deepLink) +
      `<div class="card"><div class="section-title">Monitoring approach</div><p class="muted">The monitoring job (Evidently 0.7.x) compares a reference window against the current era across the full feature set and the model's prediction score, and writes a JSON summary. Prediction-drift is also monitored on real served scores via the inference audit log. Re-run <span class="mono">ml/finlens_ml/monitor.py</span> to refresh the report.</p>
      <table class="tbl" style="margin-top:12px"><thead><tr><th>Signal</th><th>Method</th><th>Why</th></tr></thead><tbody>
      ${[["Data drift", "PSI / Wasserstein per feature", "input distribution shift"], ["Prediction drift", "score-distribution shift", "earliest warning (labels lag)"], ["Concept drift", "label-conditioned (when labels land)", "true performance change"], ["Freshness / nulls", "schema + null-rate", "pipeline health"]].map((r) => `<tr><td>${r[0]}</td><td class="mono">${r[1]}</td><td>${r[2]}</td></tr>`).join("")}</tbody></table></div>`;
  } else if (sec === "governance") {
    p.innerHTML = head("Machine Learning · Governance", "Governance & Limits", "Aligned with SR 26-2 principles (non-binding). Scoped honestly.", deepLink) +
      `<div class="grid g2">${[["SR 26-2 alignment", "Non-binding Fed/OCC/FDIC model-risk guidance; a gradient-boosted classifier is in-scope (non-generative AI). Portfolio demonstration, not a regulated production model."], ["Explainability", "SHAP drivers + economically-signed monotone constraints. Validator-facing, not consumer adverse-action."], ["Fairness scoping", "Institution-level model — no protected class; demographic-parity/disparate-impact do not apply. Assessed as performance equity across size tiers, regions, charters."], ["The rate-risk limit", "Catches credit-driven distress out-of-time; misses liquidity/rate-driven runs (SVB) absent in-regime training examples — the 2023 blind spot. HTM + uninsured features surface the vulnerability, displayed in the Lab."], ["Out-of-time evaluation", "2019+ failures are scored by a model trained only through 2018 — a genuine forward test."], ["Reproducible · $0", "Fixed seeds, pinned features, CI metric gate + an import guard that fails the build if ML code touches a paid service."]].map((c) => `<div class="card reveal"><div class="section-title">${c[0]}</div><p class="muted">${c[1]}</p></div>`).join("")}</div>`;
  } else { // lab
    renderLab(p, deepLink);
  }
}

/* ---------------- Live Stress Lab ---------------- */
function renderLab(p, deepLink) {
  p.innerHTML = head("Machine Learning · Live Stress Lab", "Live Stress Lab", "Real-time inference against the deployed model. Test a real bank and fact-check the prediction, or build a hypothetical bank.", deepLink) +
    `<div class="tabs"><button class="tab active" data-t="real">Test a real bank</button><button class="tab" data-t="hypo">Build a hypothetical bank</button></div>
     <div id="paneReal"></div><div id="paneHypo" style="display:none"></div>`;
  p.querySelectorAll(".tab").forEach((t) => t.onclick = () => { p.querySelectorAll(".tab").forEach((x) => x.classList.remove("active")); t.classList.add("active"); $("#paneReal").style.display = t.dataset.t === "real" ? "" : "none"; $("#paneHypo").style.display = t.dataset.t === "hypo" ? "" : "none"; });
  buildReal($("#paneReal")); buildHypo($("#paneHypo"));
}
function buildReal(host) {
  const banks = [...D.banks].sort((a, b) => (b.fail_year || 0) - (a.fail_year || 0) || (b.percentile || 0) - (a.percentile || 0));
  let def = 0, best = -1; banks.forEach((b, i) => { if (b.held_out && b.percentile >= 95 && (b.assets_m || 0) > best) { best = b.assets_m || 0; def = i; } });
  host.innerHTML = `<div class="filters"><label>Institution</label><select id="bankSel">${banks.map((b, i) => `<option value="${i}">${esc(b.name)} — ${b.state || "?"} · ${b.as_of} · failed ${b.fail_year}${b.held_out ? " (held-out)" : ""}</option>`).join("")}</select></div>
    <div class="lab-split"><div class="card"><div class="gauge-row"><div id="gauge" class="gauge"></div><div><div class="decision" id="rdec">—</div><div class="subtle" id="rline"></div><div class="subtle" id="rbasis"></div></div></div><div class="chart-label" style="margin-top:14px">Key risk indicators</div><div id="rind" class="chart chart-sm"></div></div>
    <aside class="card"><div class="fc-kicker">Fact check</div><div id="fc"></div></aside></div>`;
  const sel = $("#bankSel"); sel.value = def; sel.onchange = () => showBank(banks[sel.value]); showBank(banks[def]);
}
function showBank(b) {
  drawGauge("#gauge", b.percentile, "Risk pct");
  const flag = b.percentile >= 96, watch = !flag && b.percentile >= 85;
  const d = $("#rdec"); d.textContent = flag ? "FLAGGED — top-tier risk" : watch ? "ELEVATED — watchlist" : "Not flagged"; d.className = "decision " + (flag || watch ? "flag" : "clear");
  $("#rline").textContent = `Risk percentile ${fmt(b.percentile, 1)} in ${b.as_of} · calibrated p=${fmt(b.score * 100, 2)}%`;
  $("#rbasis").textContent = b.basis;
  const ind = [["Uninsured %", b.uninsured], ["HTM securities %", b.htm], ["Tier-1 capital %", b.features?.tier1_rwa_ratio], ["Noncurrent %", b.features?.noncurrent_to_loans], ["ROA %", b.features?.roa]].filter((x) => x[1] != null);
  chart($("#rind")).setOption({ grid: { left: 130, right: 40, top: 6, bottom: 22 }, tooltip: { trigger: "axis" }, xAxis: { type: "value", ...axis }, yAxis: { type: "category", data: ind.map((i) => i[0]).reverse(), ...axis }, series: [{ type: "bar", data: ind.map((i) => i[1]).reverse(), itemStyle: { color: ACC2 }, label: { show: true, position: "right", color: TXT, formatter: (p) => fmt(p.value, 1) } }] });
  const caught = b.percentile >= 96, w = !caught && b.percentile >= 85;
  const verdict = caught ? ["hit", "Model CAUGHT it"] : w ? ["watch", "Model FLAGGED as elevated"] : ["miss", "Model MISSED it"];
  const assets = b.assets_m ? `$${(b.assets_m / 1e6).toFixed(1)}B` : "—";
  let note = ""; if (b.cert === 24735) note = `<p class="subtle" style="margin-top:10px">SVB was a rate/liquidity-driven run, not credit deterioration — invisible to traditional CAMELS ratios and the 2023 blind spot. The out-of-time model (pre-2019, no rate failures to learn from) ranks it low; its HTM (${fmt(b.htm, 0)}%) and uninsured (${fmt(b.uninsured, 0)}%), shown at left, are the factors that sank it.</p>`;
  $("#fc").innerHTML = `<div class="fc-verdict ${verdict[0]}">${verdict[1]}</div><div class="fc-row"><span class="k">Outcome</span><span>Failed · ${b.fail_year}</span></div><div class="fc-row"><span class="k">Risk rank</span><span>${fmt(b.percentile, 1)}th pct</span></div><div class="fc-row"><span class="k">Assets</span><span>${assets}</span></div><div class="fc-row"><span class="k">Uninsured</span><span>${fmt(b.uninsured, 0)}%</span></div><div class="fc-row"><span class="k">Basis</span><span>${b.held_out ? "out-of-time" : "training-era"}</span></div>${note}`;
}
let hT = null, hC = null;
function buildHypo(host) {
  const sl = D.feats.sliders;
  host.innerHTML = `<div class="lab-split"><div class="card"><div class="sliders">${Object.entries(sl).map(([f, [lo, hi, d]]) => `<div class="slider"><label>${f}<span class="val" id="v_${f}">${d}</span></label><input type="range" id="s_${f}" min="${lo}" max="${hi}" value="${d}" step="${(hi - lo) / 100}"></div>`).join("")}</div></div>
    <aside class="card"><div id="hres" style="text-align:center"></div><div class="decision" id="hdec" style="text-align:center;margin-top:6px">—</div><div class="subtle" id="hline" style="text-align:center"></div><div class="chart-label" style="margin-top:12px">Why (SHAP)</div><div id="hshap" class="chart chart-sm"></div><details class="api-peek"><summary>See the live API call</summary><pre id="apiPeek">—</pre></details></aside></div>`;
  Object.keys(sl).forEach((f) => $("#s_" + f).addEventListener("input", () => { $("#v_" + f).textContent = (+$("#s_" + f).value).toFixed(1); clearTimeout(hT); hT = setTimeout(scoreHypo, 200); }));
  scoreHypo();
}
async function scoreHypo() {
  const feats = {}; Object.keys(D.feats.sliders).forEach((f) => feats[f] = +$("#s_" + f).value);
  if (hC) hC.abort(); hC = new AbortController(); const body = JSON.stringify({ features: feats }), t0 = performance.now();
  try {
    const r = await fetch("/predict", { method: "POST", headers: { "Content-Type": "application/json" }, body, signal: hC.signal });
    const d = await r.json(), ms = Math.round(performance.now() - t0), p = d.probability * 100;
    $("#hres").innerHTML = `<div style="font-size:2.4rem;font-weight:800;color:${d.flagged ? WARN : ACCENT}">${p.toFixed(2)}%</div><div class="subtle">distress probability (4q)</div>`;
    const dec = $("#hdec"); dec.textContent = d.flagged ? "FLAGGED for review" : "Not flagged"; dec.className = "decision " + (d.flagged ? "flag" : "clear");
    $("#hline").textContent = `threshold ${(d.threshold * 100).toFixed(0)}% · ${(d.model_version || "").split("-").slice(-1)[0]} · ${ms}ms · req ${d.request_id || ""}`;
    const rs = (d.reasons || []).slice(0, 6);
    chart($("#hshap")).setOption({ grid: { left: 150, right: 30, top: 6, bottom: 22 }, tooltip: { trigger: "axis" }, xAxis: { type: "value", ...axis }, yAxis: { type: "category", data: rs.map((x) => x.feature).reverse(), ...axis }, series: [{ type: "bar", data: rs.map((x) => ({ value: +x.shap.toFixed(3), itemStyle: { color: x.shap > 0 ? WARN : ACCENT } })).reverse(), label: { show: true, position: "right", color: TXT, formatter: (p) => p.value } }] });
    $("#apiPeek").textContent = `POST /predict\n${body}\n\n→ ${JSON.stringify({ request_id: d.request_id, probability: d.probability, flagged: d.flagged, model_version: d.model_version }, null, 1)}`;
  } catch (e) { if (e.name !== "AbortError") $("#hline").textContent = "model offline — start the API"; }
}

/* ---------------- Wiki ---------------- */
function renderWiki(v, articleSlug) {
  const arts = D.wiki.articles, slug = (t) => t.toLowerCase().replace(/[^a-z0-9]+/g, "-");
  const current = arts.find((a) => slug(a.title) === articleSlug) || arts[0];
  const rail = Object.entries(D.wiki.clusters).map(([c, titles]) => `<div class="group"><div class="rail-title">${c}</div>${titles.map((t) => `<a class="${t === current.title ? "active" : ""}" href="#/wiki/${slug(t)}">${t}</a>`).join("")}</div>`).join("");
  v.innerHTML = `<div class="surface"><nav class="rail"><div class="rail-title">Wiki</div>${rail}</nav><div class="panel"><div class="crumb">${esc(current.cluster)} / ${esc(current.branch)}</div><h2 style="font-size:1.5rem">${esc(current.title)}</h2><p class="muted" style="margin:.4rem 0 16px">${esc(current.summary)}</p><div class="card"><div id="wbody"></div></div></div></div>`;
  $("#wbody").innerHTML = mdLite(current.body);
}
function mdLite(s) {
  return esc(s).replace(/^### (.*)$/gm, "<h4>$1</h4>").replace(/^## (.*)$/gm, "<h3 style='margin:14px 0 6px'>$1</h3>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/`(.+?)`/g, "<span class='mono'>$1</span>")
    .replace(/^- (.*)$/gm, "• $1").replace(/\n{2,}/g, "<br/><br/>").replace(/\n/g, "<br/>");
}

/* ---------------- Architect's Desk ---------------- */
function renderDesk(v, parts) {
  const sub = parts[1]; // undefined | 'de' | 'ml' | 'c'
  if (sub === "c") return renderComponent(v, parts[2]);
  const tab = sub === "de" ? "de" : sub === "ml" ? "ml" : "home";
  const tabs = `<div class="tabs"><button class="tab ${tab === "home" ? "active" : ""}" onclick="location.hash='#/desk'">Flow Map</button><button class="tab ${tab === "de" ? "active" : ""}" onclick="location.hash='#/desk/de'">Data Engineering Architecture</button><button class="tab ${tab === "ml" ? "active" : ""}" onclick="location.hash='#/desk/ml'">Machine Learning Architecture</button></div>`;
  const desc = tab === "home" ? "The whole system end to end. Click any node to open its component page." : tab === "de" ? "Ingestion → medallion → quality → serving. Click a node for detail." : "Feature panel → model → registry → serving → monitoring → retrain. Click a node for detail.";
  v.innerHTML = `<div class="home"><div class="crumb">Architect's Desk</div><h2 style="font-size:1.6rem">System Architecture${tab === "home" ? " — End to End" : tab === "de" ? " — Data Engineering" : " — Machine Learning"}</h2><p class="muted" style="margin:.4rem 0 14px">${desc}</p>${tabs}<div class="card"><div class="dag-wrap" id="dag"></div></div>
    <details style="margin-top:14px"><summary class="subtle">Accessibility: component list (table fallback)</summary><div class="card" style="margin-top:8px"><table class="tbl"><thead><tr><th>Component</th><th>Layer</th><th>Status</th><th>Production ref</th><th>$0 counterpart</th></tr></thead><tbody>${D.graph.nodes.map((n) => `<tr><td><a href="${n.route}" style="color:var(--accent2)">${n.label}</a></td><td>${n.layer}</td><td><span class="pill ${n.status}">${n.status}</span></td><td>${n.prod_ref}</td><td class="mono">${n.zero_dollar}</td></tr>`).join("")}</tbody></table></div></details></div>`;
  drawDag($("#dag"), tab === "home" ? "all" : tab);
}
function drawDag(node, slice) {
  // fixed layered LR coordinates
  const layerX = { src: 0, ingest: 1, bronze: 2, silver: 3, intermediate: 4, gold: 5, biz: 6, feat: 6, model: 7, reg: 8, serve: 9, mon: 10, mlui: 10 };
  const pos = {
    fdic_src: [0, 1], fred_src: [0, 3], ingest: [1, 2], bronze: [2, 2], silver: [3, 2], intermediate: [4, 2], gold: [5, 2],
    quality: [5, 3.4], business_surfaces: [6, 0.5], feature_panel: [6, 2.4], features: [7, 2.4], train: [8, 2.4], registry: [9, 2.4], serving: [10, 2.4], audit: [11, 1.6], monitoring: [11, 3.2], ml_surfaces: [12, 2.4],
  };
  let nodes = D.graph.nodes, edges = D.graph.edges;
  if (slice === "de") nodes = nodes.filter((n) => n.layer === "de" || n.layer === "shared");
  else if (slice === "de_lineage") nodes = nodes.filter((n) => n.layer === "de");
  else if (slice === "ml") nodes = nodes.filter((n) => n.layer === "ml" || n.layer === "shared");
  const ids = new Set(nodes.map((n) => n.id));
  edges = edges.filter((e) => ids.has(e[0]) && ids.has(e[1]));
  const col = (n) => n.layer === "ml" ? ACC2 : n.layer === "de" ? ACCENT : WARN;
  // compact x: rank the distinct x-levels present in this slice so nodes spread without overlap
  const xs = [...new Set(nodes.map((n) => pos[n.id]?.[0] ?? 6))].sort((a, b) => a - b);
  const xrank = Object.fromEntries(xs.map((x, i) => [x, i]));
  const data = nodes.map((n) => ({ name: n.id, value: n.label,
    x: xrank[pos[n.id]?.[0] ?? 6] * 165, y: (pos[n.id]?.[1] ?? 2) * 88,
    itemStyle: { color: col(n) }, label: { formatter: n.label } }));
  const links = edges.map((e) => ({ source: e[0], target: e[1] }));
  const c = chart(node);
  c.setOption({
    tooltip: { formatter: (p) => p.dataType === "node" ? `${p.data.value} (click to open)` : "" },
    series: [{ type: "graph", layout: "none", roam: true, data, links, edgeSymbol: ["none", "arrow"], edgeSymbolSize: 8,
      symbol: "roundRect", symbolSize: [86, 34], itemStyle: { borderColor: "#0a0e17", borderWidth: 1 },
      label: { show: true, color: "#04140f", fontSize: 10, fontWeight: 600, width: 80, overflow: "break" },
      lineStyle: { color: "#3a4a63", width: 1.4, curveness: 0.05 }, emphasis: { focus: "adjacency", lineStyle: { color: ACCENT, width: 2 } } }],
  });
  c.off("click"); c.on("click", (p) => { if (p.dataType === "node") location.hash = `#/desk/c/${p.data.name}`; });
}
function renderComponent(v, id) {
  const n = D.graph.nodes.find((x) => x.id === id);
  if (!n) { v.innerHTML = `<div class="home"><div class="empty">Unknown component.</div></div>`; return; }
  const back = n.layer === "ml" ? "#/desk/ml" : n.layer === "de" ? "#/desk/de" : "#/desk";
  v.innerHTML = `<div class="home"><div class="crumb"><a href="${back}" style="color:var(--accent2)">← Architecture</a> · ${n.layer.toUpperCase()}</div>
    <h2 style="font-size:1.7rem">${esc(n.label)} <span class="pill ${n.status}" style="font-size:.7rem;vertical-align:middle">${n.status}</span></h2>
    <div class="comp-meta">
      <div class="kv"><div class="k">Production reference</div><div class="v">${esc(n.prod_ref)}</div></div>
      <div class="kv"><div class="k">$0 counterpart (this build)</div><div class="v">${esc(n.zero_dollar)}</div></div>
      <div class="kv"><div class="k">Layer</div><div class="v">${n.layer}</div></div>
      <div class="kv"><div class="k">Source artifact</div><div class="v mono">${esc(n.artifact_path)}</div></div>
    </div>
    <div class="card" style="margin-top:16px"><div class="section-title">Role in the pipeline</div><p class="muted">${compBlurb(n)}</p></div>
    <div class="side-links"><a href="${back}">← Back to the map</a></div></div>`;
}
function compBlurb(n) {
  const m = {
    fdic_src: "Free FDIC BankFind API supplies per-institution quarterly Call Report financials and the failed-bank list — the raw substrate for the whole system.",
    fred_src: "Free FRED/ALFRED API supplies macro series as-released (vintage) so macro features carry no look-ahead.",
    ingest: "HTTP pull lands raw source payloads locally (no Kafka/S3 needed at this cadence). Paginated, schema-checked.",
    bronze: "Immutable raw layer — source fidelity preserved before any transform.",
    silver: "dbt staging models normalize raw payloads into canonical, typed tables.",
    intermediate: "dbt intermediate models hold reusable business logic (e.g. failures joined with macro context).",
    gold: "Dimensional marts (Kimball) — the dashboard/serving contract.",
    quality: "Great Expectations checkpoints (on-load, on-serve) + dbt tests gate every build.",
    business_surfaces: "The Business vertical renders gold marts as the banking-stress narrative.",
    feature_panel: "Point-in-time bank-quarter panel in DuckDB — the offline feature substrate (a full feature store is overkill at quarterly cadence).",
    features: "CAMELS ratios + trends + peer z-scores + the 2023 rate-risk features (uninsured, HTM/AFS), with monotone signs.",
    train: "LightGBM discrete-time hazard model + isotonic calibration + a penalized-logit benchmark; rolling-origin out-of-time validation.",
    registry: "MLflow registry with a champion alias; promotion/rollback is a single alias repoint that serving resolves.",
    serving: "FastAPI loads the champion (registry-resolved, file fallback), returns calibrated probability + SHAP reason codes + request id.",
    audit: "Every served request is logged (inputs, version, probability, reason codes) — the MRM/audit spine and prediction-drift source.",
    monitoring: "Evidently computes data + prediction drift; drift can trigger the retrain DAG.",
    ml_surfaces: "The ML vertical + Live Lab render model state and call serving for real-time inference.",
  };
  return m[n.id] || "Component of the FinLens pipeline.";
}

/* gauge */
function drawGauge(el, value, label) {
  const col = value >= 96 ? DANGER : value >= 85 ? WARN : ACCENT;
  chart($(el)).setOption({ series: [{ type: "gauge", min: 0, max: 100, radius: "100%", center: ["50%", "60%"], progress: { show: true, width: 11, itemStyle: { color: col } }, axisLine: { lineStyle: { width: 11, color: [[1, LINE]] } }, axisTick: { show: false }, splitLine: { show: false }, axisLabel: { show: false }, pointer: { show: false }, title: { offsetCenter: [0, "28%"], color: TXT, fontSize: 11 }, detail: { offsetCenter: [0, "-6%"], formatter: (v) => v.toFixed(0), color: col, fontSize: 28, fontWeight: 800 }, data: [{ value, name: label }] }] });
}
