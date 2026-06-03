"""Pass-2 exhaustive crawler. Handles st.tabs (role=tab) and section top-tabs
(role=button), exercises predictive flows. Output -> audit/."""
import json
import os
import sys
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8613"
OUT = "audit"
os.makedirs(OUT, exist_ok=True)
SMELLS = ["NaN", "not found", "Traceback", "getaddrinfo", "KeyError", "ValueError",
          "AttributeError", " None ", "None\n", "undefined", "1980"]
manifest = []


def dismiss(pg):
    try:
        b = pg.get_by_role("button", name="I understand")
        if b.count() and b.first.is_visible():
            b.first.click()
            pg.wait_for_timeout(1500)
    except Exception:
        pass


def probe(pg, key):
    body = pg.inner_text("body")
    return {
        "key": key,
        "smell_flags": [s for s in SMELLS if s in body],
        "exception_blocks": pg.locator('[data-testid="stException"]').count(),
        "number_inputs": pg.locator('input[type="number"]').count(),
        "selectboxes": pg.locator('[data-baseweb="select"]').count(),
    }


def snap(pg, key):
    pg.wait_for_timeout(1000)
    pg.screenshot(path=f"{OUT}/{key}.png", full_page=True)
    info = probe(pg, key)
    manifest.append(info)
    print(f"{key}: exc={info['exception_blocks']} smells={info['smell_flags']} "
          f"num_inputs={info['number_inputs']}")


def click_btn(pg, label):
    try:
        b = pg.get_by_role("button", name=label, exact=True)
        if b.count():
            b.first.click()
            pg.wait_for_timeout(2200)
            return True
    except Exception:
        pass
    return False


with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={"width": 1600, "height": 1100})
    errs = []
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)

    pg.goto(BASE + "/", wait_until="networkidle", timeout=60000)
    pg.wait_for_timeout(2500)
    dismiss(pg)
    snap(pg, "01_home")

    for path, key in [("/Stress_Pulse", "10_biz_stress"), ("/Banks", "11_biz_failures"),
                      ("/Metrics", "12_biz_macro"), ("/Wiki", "60_wiki")]:
        pg.goto(BASE + path, wait_until="networkidle", timeout=60000)
        pg.wait_for_timeout(2500)
        dismiss(pg)
        snap(pg, key)

    # PREDICTIVE — proper role=tab handling
    pg.goto(BASE + "/Predictive_Analytics", wait_until="networkidle", timeout=60000)
    pg.wait_for_timeout(2600)
    dismiss(pg)
    tabs = pg.get_by_role("tab")
    names = ["13a_pred_score", "13b_pred_holdout", "13c_pred_whatif"]
    for i in range(min(tabs.count(), 3)):
        tabs.nth(i).click()
        pg.wait_for_timeout(2600)
        snap(pg, names[i])

    # DE sections
    pg.goto(BASE + "/Under_The_Hood", wait_until="networkidle", timeout=60000)
    pg.wait_for_timeout(2600)
    dismiss(pg)
    snap(pg, "40_de_pipeline")
    for label, key in [("Source Contracts", "41_de_contracts"),
                       ("Engineering Stack", "42_de_stack"),
                       ("Data Quality", "43_de_quality"),
                       ("Architecture Decisions", "44_de_decisions"),
                       ("Administration", "45_de_admin")]:
        if click_btn(pg, label):
            snap(pg, key)

    # AI sections
    pg.goto(BASE + "/AI_Engineering", wait_until="networkidle", timeout=60000)
    pg.wait_for_timeout(2600)
    dismiss(pg)
    snap(pg, "70_ai_pipeline")
    for label, key in [("Feature Contracts", "71_ai_contracts"),
                       ("AI Stack", "72_ai_stack"),
                       ("Model Quality", "73_ai_quality"),
                       ("Model Decisions", "74_ai_decisions"),
                       ("Administration", "75_ai_admin"),
                       ("AI Wiki", "76_ai_wiki")]:
        if click_btn(pg, label):
            snap(pg, key)

    real = [e for e in errs if "404" not in e]
    json.dump({"screens": manifest, "console_errors": real},
              open(f"{OUT}/manifest.json", "w"), indent=2)
    print("\nconsole_errors:", len(real), "screens:", len(manifest))
    br.close()
