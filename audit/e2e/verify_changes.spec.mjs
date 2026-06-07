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
  await page.waitForTimeout(1000);
}

test("DE pipeline shows VPS storage card, not AWS S3", async ({ page }) => {
  await page.goto("/Data_Engineering"); await settle(page);
  await expect(page.getByText("VPS storage", { exact: false }).first()).toBeVisible();
  await expect(page.getByText("AWS S3")).toHaveCount(0);
  await page.screenshot({ path: `${SHOTS}de_vps_card.png`, fullPage: true });
});

test("hamburger Home navigates back to home", async ({ page }) => {
  // The centered brand wordmark + 'Switch surface' were replaced by the persistent Menu hamburger;
  // Home now lives inside that panel and must work from any sub-page.
  await page.goto("/Data_Engineering"); await settle(page);
  await page.getByRole("button", { name: "Menu" }).click();
  await page.locator('[class*="st-key-ham_home"] button').first().click();
  await settle(page);
  // navigating home may surface the use-notice gate; ack it so the hero can paint
  const ack = page.getByRole("button", { name: "I understand" });
  if (await ack.isVisible().catch(() => false)) {
    await ack.click();
    await ack.waitFor({ state: "detached", timeout: 10000 }).catch(() => {});
    await settle(page);
  }
  // home hero subline lives only on the landing page
  await expect(page.getByText("Browse the project", { exact: false }).first()).toBeVisible({ timeout: 30000 });
  await page.screenshot({ path: `${SHOTS}brand_to_home.png`, fullPage: true });
});

test("AI research write-up has no dead .md hyperlinks", async ({ page }) => {
  await page.goto("/AI_Engineering"); await settle(page);
  await page.getByText("Research write-up", { exact: false }).first().click();
  await page.waitForTimeout(1500);
  // no rendered anchor should point at a relative .md file
  const mdLinks = await page.locator('a[href$=".md"]').count();
  expect(mdLinks).toBe(0);
  await page.screenshot({ path: `${SHOTS}ai_research_writeup.png`, fullPage: true });
});

test("wiki glossary renders the expanded abbreviations", async ({ page }) => {
  await page.goto("/Wiki?article=glossary"); await settle(page);
  // wiki content lives in the SPA components iframe
  const frame = page.frameLocator("iframe").last();
  await expect(frame.getByText("CAMELS", { exact: false }).first()).toBeVisible({ timeout: 30000 });
  await expect(frame.getByText("PR-AUC", { exact: false }).first()).toBeVisible();
  await page.screenshot({ path: `${SHOTS}wiki_glossary.png`, fullPage: true });
});
