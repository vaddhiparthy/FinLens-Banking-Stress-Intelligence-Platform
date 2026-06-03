"use strict";
const $ = (s, r = document) => r.querySelector(s);
const fmt = (n, d = 2) => (n == null || Number.isNaN(n) ? "—" : Number(n).toFixed(d));
const J = (p) => fetch(p).then((r) => (r.ok ? r.json() : Promise.reject(r.status)));

const CHART_TXT = "#94a3b8", ACCENT = "#2dd4bf", WARN = "#f5a524", DANGER = "#f87171", LINE = "#222b3d";
const baseGrid = { left: 48, right: 18, top: 24, bottom: 36 };
const axisStyle = { axisLine: { lineStyle: { color: LINE } }, axisLabel: { color: CHART_TXT }, splitLine: { lineStyle: { color: LINE } } };

let META, PERF, BANKS, FEATURES;

document.addEventListener("DOMContentLoaded", init);

async function init() {
  pollApi();
  setInterval(pollApi, 15000);
  try {
    [META, PERF, BANKS, FEATURES] = await Promise.all([
      J("/data/meta.json"), J("/data/performance.json"), J("/data/banks.json"), J("/data/features.json"),
    ]);
  } catch (e) { console.error("data load failed", e); return; }
  renderHero(); renderTimeline(); renderPipeline(); renderPerformance(); renderGovernance(); renderStack();
  setupTabs(); setupRealBank(); setupHypothetical(); setupReveal();
}

/* ---------- API status badge (live proof) ---------- */
async function pollApi() {
  const b = $("#apiBadge"), t = $("#apiText");
  const t0 = performance.now();
  try {
    const r = await J("/ready"); const ms = Math.round(performance.now() - t0);
    b.className = "api-badge online"; t.textContent = `model online · ${r.model_version?.split("-").slice(-1)[0] || "v"} · ${ms}ms`;
  } catch { b.className = "api-badge offline"; t.textContent = "model offline"; }
}

/* ---------- hero ---------- */
function renderHero() {
  const o = META.oot;
  const stats = [
    { v: `${o.pr_auc}`, l: `PR-AUC out-of-time (vs ${o.logit_pr_auc} logit benchmark)`, good: true },
    { v: `${(o.recall_at_k * 100).toFixed(0)}%`, l: `recall @ top ${o.k} flagged banks`, good: true },
    { v: `${META.n_features}`, l: "CAMELS + rate-risk features" },
    { v: `${o.base_rate_pct}%`, l: `base rate (${o.failures} of ${o.n_test.toLocaleString()})` },
  ];
  $("#heroStats").innerHTML = stats.map((s) =>
    `<div class="stat"><div class="v ${s.good ? "good" : ""}">${s.v}</div><div class="l">${s.l}</div></div>`).join("");
}

/* ---------- charts ---------- */
function mk(el) { const c = echarts.init($(el), null, { renderer: "canvas" }); addEventListener("resize", () => c.resize()); return c; }

function renderTimeline() {
  J("/data/timeline.json").then((tl) => {
    const c = mk("#timelineChart");
    c.setOption({
      grid: baseGrid, tooltip: { trigger: "axis" },
      xAxis: { type: "category", data: tl.map((d) => d.quarter), ...axisStyle,
        axisLabel: { color: CHART_TXT, interval: 7 } },
      yAxis: { type: "value", name: "failures", ...axisStyle },
      series: [{ type: "bar", data: tl.map((d) => d.failures), itemStyle: { color: ACCENT } }],
    });
  });
}

function renderPerformance() {
  const o = META.oot;
  $("#perfNote").textContent = `Out-of-time test: ${o.n_test.toLocaleString()} bank-quarters, ${o.failures} real failures (${o.window_q} quarters). PR-AUC is the headline; ROC-AUC is comparability-only.`;
  $("#whyText").textContent = `At a ${o.base_rate_pct}% base rate (${o.failures} failures in ${o.n_test.toLocaleString()} bank-quarters), accuracy is meaningless — a model predicting "no bank ever fails" scores ${(100 - o.base_rate_pct).toFixed(2)}%. ROC-AUC is also optimistic under extreme imbalance. Precision–Recall (PR-AUC) measures whether the model actually surfaces the rare failures: ${o.pr_auc} vs ${o.logit_pr_auc} for the regulatory logistic benchmark. Calibration ECE ${o.ece != null ? o.ece.toExponential(1) : "—"}.`;

  const pr = mk("#prChart");
  pr.setOption({
    grid: baseGrid, tooltip: { trigger: "axis" },
    legend: { textStyle: { color: CHART_TXT }, top: 0 },
    xAxis: { type: "value", name: "recall", min: 0, max: 1, ...axisStyle },
    yAxis: { type: "value", name: "precision", min: 0, max: 1, ...axisStyle },
    series: [{ name: `model (PR-AUC ${o.pr_auc})`, type: "line", smooth: true, showSymbol: false,
      data: PERF.pr_curve, lineStyle: { color: ACCENT, width: 2.5 }, areaStyle: { color: "rgba(45,212,191,.12)" } }],
  });

  const yc = mk("#yearChart");
  const yrs = PERF.by_year.filter((y) => y.roc_auc != null);
  yc.setOption({
    grid: baseGrid, tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: yrs.map((y) => y.year), ...axisStyle },
    yAxis: { type: "value", name: "ROC-AUC", min: 0, max: 1, ...axisStyle },
    series: [{ type: "bar", data: yrs.map((y) => ({ value: y.roc_auc,
      itemStyle: { color: y.roc_auc >= 0.8 ? ACCENT : WARN } })),
      label: { show: true, position: "top", color: CHART_TXT, formatter: (p) => p.value } }],
  });
}

/* ---------- pipeline ---------- */
function renderPipeline() {
  const stages = [
    ["01", "Ingest", "Per-CERT FDIC Call Reports (free API) → DuckDB point-in-time panel"],
    ["02", "Features", `${META.n_features} CAMELS + rate-risk ratios, trends, peer z-scores`],
    ["03", "Label", "Fails-within-4q, merger/end-of-data censoring (leakage-free)"],
    ["04", "Model", "LightGBM monotone hazard + isotonic calibration"],
    ["05", "Serve", "FastAPI · calibrated probability + SHAP · live"],
    ["06", "Monitor", "Evidently data + prediction drift; quarterly retrain"],
  ];
  $("#pipeline").innerHTML = stages.map(([n, h, p]) =>
    `<div class="stage reveal"><div class="n">${n}</div><h4>${h}</h4><p>${p}</p></div>`).join("");
}

/* ---------- governance ---------- */
function renderGovernance() {
  const items = [
    ["Aligned with SR 26-2 principles", "Non-binding Fed/OCC/FDIC model-risk guidance (Apr 2026). A gradient-boosted classifier is in-scope (non-generative AI). This is a portfolio demonstration, not a regulated production model."],
    ["Explainability", "SHAP drivers per prediction + economically-signed monotone constraints (more capital never raises predicted risk). Validator-facing, not consumer adverse-action."],
    ["Fairness, scoped honestly", "An institution-level model has no protected class, so demographic-parity / disparate-impact do not apply. Assessed instead as performance equity across asset-size tiers, regions, and charter classes."],
    ["The rate-risk limit", "The model catches credit-driven distress out-of-time, but misses liquidity/rate-driven runs like SVB when no such failures exist in training — the exact 2023 supervisory blind spot. The HTM + uninsured-deposit features surface the vulnerability once peer examples exist."],
    ["No fabrication", "Every figure here is computed from real FDIC data and the trained model. Held-out banks (2019+) are scored by a model trained only on ≤2018 — genuinely out-of-time."],
    ["Reproducible & $0", "Fixed seeds, pinned features, CI metric gate + an import guard that fails the build if the ML code ever touches a paid service. Free public data only."],
  ];
  $("#govGrid").innerHTML = items.map(([h, p]) => `<div class="gov reveal"><h4>${h}</h4><p>${p}</p></div>`).join("");
}

function renderStack() {
  $("#stackChips").innerHTML = ["FDIC API", "DuckDB", "LightGBM", "scikit-learn", "SHAP", "MLflow", "FastAPI", "Evidently", "ECharts"]
    .map((t) => `<span class="chip">${t}</span>`).join("");
}

/* ---------- tabs ---------- */
function setupTabs() {
  document.querySelectorAll(".tab").forEach((t) => t.onclick = () => {
    document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
    t.classList.add("active");
    $("#pane-real").classList.toggle("hidden", t.dataset.tab !== "real");
    $("#pane-hypo").classList.toggle("hidden", t.dataset.tab !== "hypo");
  });
}

/* ---------- real-bank lab ---------- */
function setupRealBank() {
  const sel = $("#bankSelect");
  // sort: recent failures first, strong hits surfaced; SVB included as stress case
  const banks = [...BANKS].sort((a, b) => (b.fail_year || 0) - (a.fail_year || 0) || (b.percentile || 0) - (a.percentile || 0));
  sel.innerHTML = banks.map((b, i) =>
    `<option value="${i}">${b.name} — ${b.state || "?"} · ${b.as_of} · failed ${b.fail_year} ${b.held_out ? "(held-out)" : ""}</option>`).join("");
  sel._banks = banks;
  // default: a strong, recent, out-of-time HIT
  const def = banks.findIndex((b) => b.held_out && b.percentile >= 95);
  sel.value = def >= 0 ? def : 0;
  sel.onchange = () => showBank(banks[sel.value]);
  showBank(banks[sel.value]);
}

function showBank(b) {
  $("#bankHint").textContent = b.basis || "";
  // gauge = risk percentile
  drawGauge("#gauge", b.percentile, "Risk percentile");
  const flagged = b.percentile >= 96; // top ~4% review budget
  const dec = $("#realDecision");
  dec.textContent = flagged ? "FLAGGED — top-tier risk" : (b.percentile >= 85 ? "ELEVATED — watchlist" : "Not flagged");
  dec.className = "decision " + (flagged ? "flag" : (b.percentile >= 85 ? "flag" : "clear"));
  $("#realScoreLine").textContent = `Risk percentile ${fmt(b.percentile, 1)} of all banks in ${b.as_of} · calibrated p=${fmt(b.score * 100, 2)}%`;
  $("#realBasis").textContent = b.basis;
  // key indicators bar
  const ind = [
    ["Uninsured deposits %", b.uninsured, 100],
    ["HTM securities %", b.htm, 80],
    ["Tier-1 capital %", b.features?.tier1_rwa_ratio, 25],
    ["Noncurrent loans %", b.features?.noncurrent_to_loans, 15],
    ["ROA %", b.features?.roa, 3],
  ].filter((x) => x[1] != null);
  const c = mk("#driversChart");
  $(".drivers-title").textContent = "Key risk indicators";
  c.setOption({
    grid: { left: 140, right: 30, top: 8, bottom: 24 }, tooltip: { trigger: "axis" },
    xAxis: { type: "value", ...axisStyle }, yAxis: { type: "category", data: ind.map((i) => i[0]).reverse(), ...axisStyle },
    series: [{ type: "bar", data: ind.map((i) => i[1]).reverse(),
      itemStyle: { color: ACCENT }, label: { show: true, position: "right", color: CHART_TXT, formatter: (p) => fmt(p.value, 1) } }],
  });
  renderFactCheck(b, flagged);
}

function renderFactCheck(b, flagged) {
  const caught = b.percentile >= 96;
  const watch = !caught && b.percentile >= 85;
  const verdict = caught ? ["hit", "Model CAUGHT it"] : watch ? ["watch", "Model FLAGGED as elevated"] : ["miss", "Model MISSED it"];
  const assets = b.assets_m ? `$${(b.assets_m / 1e6).toFixed(1)}B` : "—";
  let note = "";
  if (b.cert === 24735) note = `<p class="subtle" style="margin-top:10px">SVB was a rate/liquidity-driven run, not credit deterioration — invisible to traditional CAMELS ratios and the exact blind spot that surprised regulators in 2023. The out-of-time model (trained pre-2019, no rate failures to learn from) misses it. Trained on SVB's 2023 peers, the same features rank it top ~10% (leave-one-out).</p>`;
  $("#fcBody").innerHTML = `
    <div class="fc-verdict ${verdict[0]}">${verdict[1]}</div>
    <div class="fc-row"><span class="k">Outcome</span><span>Failed · ${b.fail_year}</span></div>
    <div class="fc-row"><span class="k">Model risk rank</span><span>${fmt(b.percentile, 1)}th pct</span></div>
    <div class="fc-row"><span class="k">Assets</span><span>${assets}</span></div>
    <div class="fc-row"><span class="k">Uninsured deposits</span><span>${fmt(b.uninsured, 0)}%</span></div>
    <div class="fc-row"><span class="k">Basis</span><span>${b.held_out ? "out-of-time" : "training-era"}</span></div>
    ${note}`;
}

/* ---------- hypothetical lab (LIVE inference) ---------- */
let hypoTimer = null, hypoCtrl = null;
function setupHypothetical() {
  const wrap = $("#sliders"); const sl = FEATURES.sliders;
  wrap.innerHTML = Object.entries(sl).map(([f, [lo, hi, d]]) =>
    `<div class="slider"><label>${f}<span class="val" id="v_${f}">${d}</span></label>
     <input type="range" id="s_${f}" min="${lo}" max="${hi}" value="${d}" step="${(hi - lo) / 100}"></div>`).join("");
  Object.keys(sl).forEach((f) => $("#s_" + f).addEventListener("input", () => {
    $("#v_" + f).textContent = (+$("#s_" + f).value).toFixed(1); scheduleHypo();
  }));
  scoreHypo();
}
function scheduleHypo() { clearTimeout(hypoTimer); hypoTimer = setTimeout(scoreHypo, 200); }
async function scoreHypo() {
  const feats = {}; Object.keys(FEATURES.sliders).forEach((f) => feats[f] = +$("#s_" + f).value);
  if (hypoCtrl) hypoCtrl.abort(); hypoCtrl = new AbortController();
  const body = JSON.stringify({ features: feats });
  const t0 = performance.now();
  try {
    const r = await fetch("/predict", { method: "POST", headers: { "Content-Type": "application/json" }, body, signal: hypoCtrl.signal });
    const d = await r.json(); const ms = Math.round(performance.now() - t0);
    const p = d.probability * 100;
    $("#gaugeH").innerHTML = `<div style="text-align:center"><div style="font-size:2.6rem;font-weight:800;color:${d.flagged ? WARN : ACCENT}">${p.toFixed(2)}%</div><div class="subtle">distress probability (4q)</div></div>`;
    const dec = $("#hypoDecision"); dec.textContent = d.flagged ? "FLAGGED for review" : "Not flagged";
    dec.className = "decision " + (d.flagged ? "flag" : "clear");
    $("#hypoScoreLine").textContent = `threshold ${(d.threshold * 100).toFixed(0)}% · model ${d.model_version?.split("-").slice(-1)[0]} · ${ms}ms`;
    const reasons = (d.reasons || []).slice(0, 6);
    const c = mk("#driversChartH");
    c.setOption({
      grid: { left: 150, right: 30, top: 8, bottom: 24 }, tooltip: { trigger: "axis" },
      xAxis: { type: "value", ...axisStyle },
      yAxis: { type: "category", data: reasons.map((x) => x.feature).reverse(), ...axisStyle },
      series: [{ type: "bar", data: reasons.map((x) => ({ value: +x.shap.toFixed(3),
        itemStyle: { color: x.shap > 0 ? WARN : ACCENT } })).reverse(),
        label: { show: true, position: "right", color: CHART_TXT, formatter: (p) => p.value } }],
    });
    $("#apiPeek").textContent = `POST /predict\n${body}\n\n→ ${JSON.stringify({ probability: d.probability, flagged: d.flagged, model_version: d.model_version }, null, 1)}`;
  } catch (e) { if (e.name !== "AbortError") $("#hypoScoreLine").textContent = "model offline"; }
}

/* ---------- gauge + reveal ---------- */
function drawGauge(el, value, label) {
  const c = mk(el);
  const col = value >= 96 ? DANGER : value >= 85 ? WARN : ACCENT;
  c.setOption({
    series: [{ type: "gauge", min: 0, max: 100, radius: "100%", center: ["50%", "62%"],
      progress: { show: true, width: 12, itemStyle: { color: col } },
      axisLine: { lineStyle: { width: 12, color: [[1, LINE]] } },
      axisTick: { show: false }, splitLine: { show: false }, axisLabel: { show: false }, pointer: { show: false },
      anchor: { show: false }, title: { offsetCenter: [0, "30%"], color: CHART_TXT, fontSize: 11 },
      detail: { valueAnimation: true, offsetCenter: [0, "-5%"], formatter: (v) => v.toFixed(0), color: col, fontSize: 30, fontWeight: 800 },
      data: [{ value, name: label }] }],
  });
}
function setupReveal() {
  const io = new IntersectionObserver((es) => es.forEach((e) => e.isIntersecting && e.target.classList.add("in")), { threshold: 0.12 });
  document.querySelectorAll(".reveal").forEach((n) => io.observe(n));
}
