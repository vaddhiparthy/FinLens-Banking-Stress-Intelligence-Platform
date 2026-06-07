import { test, expect } from "@playwright/test";
import fs from "node:fs";

const SHOTS = new URL("../screenshots/", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
fs.mkdirSync(SHOTS, { recursive: true });

async function settle(page) {
  await page.waitForSelector('[data-testid="stApp"]', { timeout: 30_000 });
  await page.waitForFunction(() => {
    const r = document.querySelector('[data-testid="stStatusWidget"]');
    return !r || !/running/i.test(r.textContent || "");
  }, { timeout: 30_000 }).catch(() => {});
  await page.waitForTimeout(1200);
}

test("floating assistant opens and answers a cached example", async ({ page }) => {
  await page.goto("/");
  await settle(page);
  // Dismiss the first-visit use-notice gate if present.
  const ack = page.getByRole("button", { name: "I understand" });
  if (await ack.isVisible().catch(() => false)) {
    await ack.click();
    await settle(page);
  }
  // Launcher present bottom-right on the home page.
  const launch = page.getByRole("button", { name: "Ask FinLens" });
  await expect(launch).toBeVisible();
  await launch.click();
  await settle(page);
  await expect(page.getByText("FinLens Assistant").first()).toBeVisible();
  // A cached example answers instantly (no live model needed).
  await page.getByRole("button", { name: /addressable PR-AUC/i }).click();
  await settle(page);
  await expect(page.getByText(/addressable/i).first()).toBeVisible();
  await page.screenshot({ path: `${SHOTS}e2e_chat_widget.png`, fullPage: false });
});

test("bank report page renders for an institution", async ({ page }) => {
  await page.goto("/Bank_Report");
  await settle(page);
  await expect(page.getByText("Bank Distress Report").first()).toBeVisible();
  await expect(page.getByText("Executive assessment").first()).toBeVisible();
  await expect(page.getByText(/4-quarter distress probability/i).first()).toBeVisible();
  await page.screenshot({ path: `${SHOTS}e2e_bank_report.png`, fullPage: false });
});
