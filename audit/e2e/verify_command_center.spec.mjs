import { test, expect } from "@playwright/test";
import fs from "node:fs";

const SHOTS = new URL("../screenshots/verify/", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
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
  await b.waitFor({ state: "visible", timeout: 8000 }).catch(() => {});
  if (await b.isVisible().catch(() => false)) {
    await b.click();
    await b.waitFor({ state: "detached", timeout: 10000 }).catch(() => {});
    await settle(page);
  }
}

test("home command center: Live Overview renders KPIs + top risk", async ({ page }) => {
  await page.goto("/"); await settle(page); await ack(page);
  await expect(page.getByText("OOT PR-AUC").first()).toBeVisible({ timeout: 30000 });
  await expect(page.getByText("Highest modelled distress right now").first()).toBeVisible();
  // AI surface card comes first now
  await expect(page.getByText("Enter AI Engineering").first()).toBeVisible();
  await page.waitForTimeout(800);
  await page.screenshot({ path: `${SHOTS}cc_overview.png`, fullPage: true });
});

test("home command center: ML Inference tab opens on peak distress", async ({ page }) => {
  await page.goto("/"); await settle(page); await ack(page);
  await page.getByRole("tab", { name: /ML Inference/i }).click(); await settle(page);
  await page.locator('[data-testid="stSlider"]').first().waitFor({ timeout: 30000 });
  // gauge renders
  await page.waitForFunction(() => document.querySelectorAll(".js-plotly-plot").length >= 1,
    { timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(800);
  await page.screenshot({ path: `${SHOTS}cc_inference.png`, fullPage: true });
});

test("chat launcher is renamed to Research a bank", async ({ page }) => {
  await page.goto("/AI_Engineering"); await settle(page);
  await expect(page.getByRole("button", { name: "Research a bank" })).toBeVisible({ timeout: 30000 });
});
