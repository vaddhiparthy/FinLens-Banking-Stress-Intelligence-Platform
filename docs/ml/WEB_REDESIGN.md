# FinLens — Web Experience Redesign (from scratch)

Status: DESIGN — pending stringent UI/portfolio-design reviewer sign-off (100% required) before build.
Goal: sell Surya's profile (Senior Data Engineer → MLE) with ONE cohesive, elegant, interactive
experience that *proves* a real model is deployed and doing live inference. Not a text dump, not three
disjoint button-surfaces, not an "ugly PDF". $0, existing resources.

## 0. What's wrong with the current site (being scrapped)
- Default-Streamlit chrome: giant "Current Surface" buttons, three siloed surfaces, walls of text.
- No live inference UI, no visualizations, no way to test/hold-out a bank.
- Amateur self-referential commentary ("Calibration (honest)", "no fabrication") in a portfolio. Removed.

## 1. Approach / tech ($0, existing resources, max design control)
- **Bespoke single-page frontend**: hand-built HTML + modern CSS (CSS grid/flex, custom design system) +
  vanilla JS. Charts via a vendored OSS lib (Apache ECharts, MIT, downloaded once — $0, no CDN/runtime cost).
- **Served by the existing FastAPI** (`serve.py`) via StaticFiles at `/`; the SAME app exposes the live
  inference endpoints. One process, runs locally and on the existing VPS/Caddy. Streamlit is retired for the
  public face (its code/pages stay only as internal tooling, not the portfolio surface).
- **Live inference**: the lab calls `POST /predict` in real time; a header badge pings `/ready` and shows
  "Model API · online · v<hash>" + response latency → visible proof of deployment.
- Build-time JSON baked from real artifacts (`metrics_h4.json`, `drift_report.json`, a banks index with
  real features, failures-over-time, performance curves) via a small exporter script.

## 2. Information architecture — ONE scrolling narrative (sticky anchor nav, smooth-scroll, no reloads)
The three "views" are woven into a single story, not separate pages:

```
┌───────────────────────────────────────────────────────────────────────────┐
│ FinLens   ·  Overview  Live Lab  How it works  Performance  Governance      │  ← sticky top nav
│                                              [● Model API online · v9f5 · 12ms]│     (anchor links)
├───────────────────────────────────────────────────────────────────────────┤
│ HERO                                                                          │
│  Bank Financial-Distress Early-Warning                                        │
│  A production-grade ML system on 448,661 FDIC bank-quarters.                  │
│  [ PR-AUC 0.22 vs 0.11 logit ]  [ 8,803 banks ]  [ 2008–2026 ]  [ live ]      │
│  Surya Vaddhiparthy · Senior Data Engineer → MLE          [Try the Live Lab →]│
├───────────────────────────────────────────────────────────────────────────┤
│ THE PROBLEM  (Business view, visualized)                                      │
│  short framing + chart: US bank failures by quarter (2008-12 wave, 2023 SVB)  │
├───────────────────────────────────────────────────────────────────────────┤
│ ★ LIVE STRESS-TEST LAB  (centerpiece — real-time inference)                    │
│  Tabs:  [ Test a real bank ]   [ Build a hypothetical bank ]                   │
│                                                                               │
│  ── Test a real bank ───────────────────────────────────────────────────────│
│  Select: [ Silicon Valley Bank (2022) ▾]   (searchable; failed banks marked)  │
│  ┌──────────────────────────── 75% ───────────────────┐ ┌──── 25% ──────────┐│
│  │  Distress probability      ◗ 0.7%  gauge            │ │  FACT CHECK        ││
│  │  Decision: not flagged / FLAGGED                    │ │  Silicon Valley    ││
│  │  Top drivers (SHAP)  ▇▇▇▇ uninsured 94%             │ │  Bank FAILED       ││
│  │                      ▇▇▇ securities 56%             │ │  Mar 10, 2023      ││
│  │  CAMELS trajectory (line chart over quarters)       │ │  Predicted: ✓/✗    ││
│  │                                                     │ │  $209B assets,     ││
│  │                                                     │ │  94% uninsured     ││
│  └─────────────────────────────────────────────────────┘ └───────────────────┘│
│                                                                               │
│  ── Build a hypothetical bank ───────────────────────────────────────────────│
│  sliders: tier1 capital, ROA, noncurrent loans, uninsured %, securities %,    │
│  loans/deposits …  →  live gauge + decision + SHAP reasons (re-scores on drag) │
├───────────────────────────────────────────────────────────────────────────┤
│ HOW IT WORKS  (Data Engineering + AI woven into one pipeline diagram)          │
│  Ingest → Point-in-time panel → 32 CAMELS features → Hazard model →            │
│  Calibration → FastAPI serving → Evidently drift   (each stage = a card)       │
├───────────────────────────────────────────────────────────────────────────┤
│ PERFORMANCE  (real charts, not tables)                                         │
│  • Precision-Recall curve (LGBM vs logit)   • Calibration reliability curve    │
│  • ROC-AUC by year (bars)                   • Cross-segment equity (small mult)│
├───────────────────────────────────────────────────────────────────────────┤
│ GOVERNANCE & LIMITS  (concise, factual)                                        │
│  SR 26-2 alignment · SHAP transparency · cross-segment equity · the honest     │
│  rate-risk limitation (what the model sees and what it doesn't)                │
├───────────────────────────────────────────────────────────────────────────┤
│ FOOTER  built by · stack chips (FDIC · DuckDB · LightGBM · MLflow · FastAPI …) │
└───────────────────────────────────────────────────────────────────────────┘
```

## 3. The Live Lab (the thing the current site totally lacks) — exact behavior
- **Test a real bank**: pick any institution (failed ones badged). LEFT 75%: animated gauge of calibrated
  distress probability, decision chip, SHAP driver bars, and the bank's real CAMELS trajectory. RIGHT 25%:
  **Fact Check** — the real outcome (failed + date, or active), a predicted-vs-actual verdict (Hit / Miss /
  Correct-survive), and headline real figures (assets, uninsured %). For SVB the fact-check states it failed
  Mar 10 2023 and shows whether the model (now with the uninsured-deposit feature) caught it.
- **Build a hypothetical bank**: CAMELS sliders; every change fires a real `/predict` call → live gauge +
  reasons. Proof of real-time inference.
- Loading/latency states; graceful "API offline" message if `/ready` fails.

## 4. Visual system (premium fintech, not default Streamlit)
- Dark theme: near-black navy canvas (#0B0F1A), elevated cards (#121826), one accent (electric teal #2DD4BF)
  + a warning amber (#F5A524) for "flagged/failed". Generous whitespace, 8-pt grid.
- Type: Inter / system stack; large confident headings; tabular figures for metrics.
- Motion: subtle fade/slide on scroll-into-view; gauge animates; smooth-scroll anchors. No gimmicks.
- Fully responsive (desktop-first, works on mobile). Accessible contrast.

## 5. No fabrication / honesty (without announcing it)
- Every number rendered from real artifacts or a live model call. No invented figures.
- Limitations stated as plain fact (no "(honest)"/"no fabrication" meta-labels anywhere in the UI).
- If the model genuinely misses a case (e.g. SVB pre-feature), the Fact Check shows it as a Miss and the
  Governance section explains the failure mode — sophistication, not spin.

## 6. Build plan (after design sign-off)
1. `web/` static frontend: index.html, styles.css, app.js, vendored echarts.min.js.
2. `ml/scripts/export_web_data.py`: bake real JSON (metrics, curves, banks index, failures series).
3. Extend `serve.py`: mount StaticFiles + a `/banks` index + reuse `/predict` (+ CORS for local).
4. Wire charts + the lab to real data/endpoints.
5. Reviewer gate (stringent 30-yr portfolio/UI designer) → 100%. Then P7 local deploy + final QA.

## 7. Non-negotiable acceptance (what the reviewer enforces)
Elegant and clearly senior; ONE cohesive experience; live inference visibly working; the real-bank
hold-out + fact-check works; hypothetical sliders re-score live; real visualizations (not text tables);
zero amateur self-commentary; $0; loads fast; sells the profile.
