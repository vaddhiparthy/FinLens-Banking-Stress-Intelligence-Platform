import { test } from "@playwright/test";
import fs from "node:fs";

const SHOTS = new URL("../screenshots/ceiling/", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
fs.mkdirSync(SHOTS, { recursive: true });

async function settle(page) {
  await page.waitForSelector('[data-testid="stApp"]', { timeout: 30_000 });
  await page.waitForFunction(() => {
    const r = document.querySelector('[data-testid="stStatusWidget"]');
    return !r || !/running/i.test(r.textContent || "");
  }, { timeout: 30_000 }).catch(() => {});
  await page.waitForTimeout(1200);
}
async function ack(page) {
  const b = page.getByRole("button", { name: "I understand" });
  if (await b.isVisible().catch(() => false)) { await b.click(); await settle(page); }
}
async function charts(page, n = 1) {
  await page.waitForFunction(
    (k) => document.querySelectorAll(".js-plotly-plot").length >= k, n, { timeout: 30_000 }
  ).catch(() => {});
  await page.waitForTimeout(1200);
}
async function text(page, t) {
  await page.getByText(t, { exact: false }).first().waitFor({ timeout: 30_000 }).catch(() => {});
}
async function sectionTab(page, name) {  // DE/AI top section tabs are st.button (role=button)
  await page.getByRole("button", { name, exact: false }).first().click();
  await settle(page);
}
const FULL = { fullPage: true };

test("home", async ({ page }) => {
  await page.goto("/"); await settle(page); await ack(page);
  await text(page, "Spotting financial stress"); await page.waitForTimeout(600);
  await page.screenshot({ path: `${SHOTS}home.png`, ...FULL });
});
test("use-notice gate", async ({ page }) => {
  await page.goto("/"); await settle(page);
  // wait for the dialog's primary CTA to paint its accent fill before capturing
  await page.waitForFunction(() => {
    const b = document.querySelector('[role="dialog"] button[kind="primary"]');
    return b && getComputedStyle(b).backgroundColor === "rgb(191, 109, 71)";
  }, { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${SHOTS}use_notice_gate.png` });
});
test("stress pulse", async ({ page }) => {
  await page.goto("/Stress_Pulse"); await settle(page); await charts(page, 1);
  await page.screenshot({ path: `${SHOTS}biz_stress_pulse.png`, ...FULL });
});
test("failure forensics", async ({ page }) => {
  await page.goto("/Failure_Forensics"); await settle(page); await charts(page, 1);
  await page.screenshot({ path: `${SHOTS}biz_failure_forensics.png`, ...FULL });
});
test("macro transmission", async ({ page }) => {
  await page.goto("/Macro_Transmission"); await settle(page); await charts(page, 2);
  await page.screenshot({ path: `${SHOTS}biz_macro.png`, ...FULL });
});
test("early warning what-if", async ({ page }) => {
  await page.goto("/Early_Warning"); await settle(page);
  await page.getByRole("tab", { name: /Hypothetical what-if/i }).click(); await settle(page);
  await page.locator('[data-testid="stSlider"]:visible').first().waitFor({ timeout: 30000 });
  await charts(page, 1);
  await page.screenshot({ path: `${SHOTS}early_warning_whatif.png`, ...FULL });
});
test("de pipeline", async ({ page }) => {
  await page.goto("/Data_Engineering"); await settle(page); await charts(page, 1);
  await page.screenshot({ path: `${SHOTS}de_pipeline.png`, ...FULL });
});
test("de data quality", async ({ page }) => {
  await page.goto("/Data_Engineering"); await settle(page);
  await sectionTab(page, "Data Quality"); await text(page, "Great Expectations Suite");
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${SHOTS}de_data_quality.png`, ...FULL });
});
test("de administration", async ({ page }) => {
  await page.goto("/Data_Engineering"); await settle(page);
  await sectionTab(page, "Administration"); await text(page, "Containerization & Kubernetes");
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${SHOTS}de_administration.png`, ...FULL });
});
test("de engineering stack", async ({ page }) => {
  await page.goto("/Data_Engineering"); await settle(page);
  await sectionTab(page, "Engineering Stack"); await text(page, "Platform Stack Readiness");
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${SHOTS}de_engineering_stack.png`, ...FULL });
});
test("ai pipeline", async ({ page }) => {
  await page.goto("/AI_Engineering"); await settle(page);
  await text(page, "Training & scoring pipeline"); await page.waitForTimeout(800);
  await page.screenshot({ path: `${SHOTS}ai_pipeline.png`, ...FULL });
});
test("ai model quality", async ({ page }) => {
  await page.goto("/AI_Engineering"); await settle(page);
  await sectionTab(page, "Model Quality"); await text(page, "PR-AUC (OOT)"); await charts(page, 2);
  await page.screenshot({ path: `${SHOTS}ai_model_quality.png`, ...FULL });
});
test("ai notebook", async ({ page }) => {
  await page.goto("/AI_Engineering"); await settle(page);
  await sectionTab(page, "Notebook");
  await page.waitForFunction(() => document.querySelectorAll("iframe").length > 0,
    { timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2500);
  await page.screenshot({ path: `${SHOTS}ai_notebook.png`, ...FULL });
});
test("wiki home", async ({ page }) => {
  await page.goto("/Wiki"); await settle(page);
  await text(page, "FinLens Wiki"); await page.waitForTimeout(600);
  await page.screenshot({ path: `${SHOTS}wiki_home.png`, ...FULL });
});
test("wiki article", async ({ page }) => {
  await page.goto("/Wiki?article=out-of-time-evaluation"); await settle(page);
  await text(page, "The embargo"); await page.waitForTimeout(600);
  await page.screenshot({ path: `${SHOTS}wiki_article.png`, ...FULL });
});
test("bank report svb", async ({ page }) => {
  await page.goto("/Bank_Report"); await settle(page);
  const combo = page.locator('[data-testid="stSelectbox"]').first();
  await combo.click(); await page.waitForTimeout(400);
  await page.keyboard.type("Silicon Valley"); await page.waitForTimeout(700);
  await page.keyboard.press("Enter"); await settle(page); await charts(page, 1);
  await page.screenshot({ path: `${SHOTS}bank_report_svb.png`, ...FULL });
});
test("chat open", async ({ page }) => {
  await page.goto("/AI_Engineering"); await settle(page);
  await page.getByRole("button", { name: "Ask FinLens" }).click(); await settle(page);
  const input = page.getByPlaceholder(/Ask a question/i);
  await input.fill("Tell me about Fifth Third Bank"); await input.press("Enter"); await settle(page);
  await text(page, "operating institution"); await page.waitForTimeout(600);
  await page.screenshot({ path: `${SHOTS}chat_open.png` });
});
