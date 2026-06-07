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
  // Use a non-gated page so the disclaimer modal never races the launcher click.
  await page.goto("/AI_Engineering");
  await settle(page);
  // Launcher present bottom-right on every page.
  const launch = page.getByRole("button", { name: "Research a bank" });
  await expect(launch).toBeVisible();
  await launch.click();
  await settle(page);
  await expect(page.getByText("FinLens Analyst").first()).toBeVisible();
  // A cached question answers instantly (no live model needed).
  const panel = page.locator(".st-key-finlens_chat_open");
  const input = page.getByPlaceholder(/Ask a question/i);
  await input.fill("What is the addressable PR-AUC and how does it differ from pooled?");
  await input.press("Enter");
  await settle(page);
  await expect(panel.getByText(/pooled out-of-time PR-AUC/i).first()).toBeVisible();
  await page.screenshot({ path: `${SHOTS}e2e_chat_widget.png`, fullPage: false });
});

test("assistant handles an operating bank by name (Comerica), not a failure dump", async ({ page }) => {
  await page.goto("/AI_Engineering");
  await settle(page);
  await page.getByRole("button", { name: "Research a bank" }).click();
  await settle(page);
  const input = page.getByPlaceholder(/Ask a question/i);
  await input.fill("What happened to Comerica Bank?");
  await input.press("Enter");
  await settle(page);
  // Must recognize it as operating, not say "no information" or dump unrelated failures.
  await expect(page.getByText(/operating institution/i).first()).toBeVisible();
  await expect(page.getByRole("button", { name: /full report on COMERICA BANK/i })).toBeVisible();
  await page.screenshot({ path: `${SHOTS}e2e_chat_comerica.png` });
});

test("bank report page renders for an institution", async ({ page }) => {
  await page.goto("/Bank_Report");
  await settle(page);
  await expect(page.getByText("Bank Distress Report").first()).toBeVisible();
  await expect(page.getByText("Executive assessment").first()).toBeVisible();
  await expect(page.getByText(/4-quarter distress probability/i).first()).toBeVisible();
  await page.screenshot({ path: `${SHOTS}e2e_bank_report.png`, fullPage: false });
});
