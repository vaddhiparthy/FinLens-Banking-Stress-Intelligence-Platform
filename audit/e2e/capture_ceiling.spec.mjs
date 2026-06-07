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
  await page.waitForTimeout(1400);
}
async function ack(page) {
  const b = page.getByRole("button", { name: "I understand" });
  if (await b.isVisible().catch(() => false)) { await b.click(); await settle(page); }
}

const FULL = { fullPage: true };

test("capture home", async ({ page }) => {
  await page.goto("/"); await settle(page); await ack(page);
  // Wait for the real hero (post-gate) before capturing.
  await page.getByText("Spotting financial stress").first().waitFor({ timeout: 30000 });
  await page.waitForTimeout(800);
  await page.screenshot({ path: `${SHOTS}home.png`, ...FULL });
});
test("capture use-notice gate", async ({ page }) => {
  await page.goto("/"); await settle(page);
  await page.screenshot({ path: `${SHOTS}use_notice_gate.png` });
});
test("capture data engineering data quality", async ({ page }) => {
  await page.goto("/Data_Engineering"); await settle(page);
  await page.getByRole("button", { name: "Data Quality" }).first().click(); await settle(page);
  await page.getByText("Great Expectations Suite").first().waitFor({ timeout: 30000 });
  await page.waitForTimeout(800);
  await page.screenshot({ path: `${SHOTS}de_data_quality.png`, ...FULL });
});
test("capture data engineering administration", async ({ page }) => {
  await page.goto("/Data_Engineering"); await settle(page);
  await page.getByRole("button", { name: "Administration" }).first().click(); await settle(page);
  await page.getByText("Containerization & Kubernetes").first().waitFor({ timeout: 30000 });
  await page.waitForTimeout(800);
  await page.screenshot({ path: `${SHOTS}de_administration.png`, ...FULL });
});
test("capture ai model quality", async ({ page }) => {
  await page.goto("/AI_Engineering"); await settle(page);
  await page.getByRole("button", { name: "Model Quality" }).first().click(); await settle(page);
  await page.getByText("PR-AUC (OOT)").first().waitFor({ timeout: 30000 });
  await page.waitForTimeout(800);
  await page.screenshot({ path: `${SHOTS}ai_model_quality.png`, ...FULL });
});
test("capture wiki article", async ({ page }) => {
  await page.goto("/Wiki?article=failure-type-decomposition"); await settle(page);
  await page.screenshot({ path: `${SHOTS}wiki_article.png`, ...FULL });
});
test("capture bank report for a failed bank", async ({ page }) => {
  await page.goto("/Bank_Report"); await settle(page);
  // pick a recognizable failed bank for the richest report (regulator record + drivers)
  const combo = page.locator('[data-testid="stSelectbox"]').first();
  await combo.click(); await page.waitForTimeout(400);
  await page.keyboard.type("Silicon Valley");
  await page.waitForTimeout(700);
  await page.keyboard.press("Enter");
  await settle(page);
  await page.screenshot({ path: `${SHOTS}bank_report_svb.png`, ...FULL });
});
test("capture chat open", async ({ page }) => {
  await page.goto("/AI_Engineering"); await settle(page);
  await page.getByRole("button", { name: "Ask FinLens" }).click(); await settle(page);
  await page.getByRole("button", { name: /addressable PR-AUC/i }).click(); await settle(page);
  await page.screenshot({ path: `${SHOTS}chat_open.png` });
});
