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

test("wiki System Architecture renders the graphviz diagram in the SPA", async ({ page }) => {
  await page.goto("/Wiki?article=system-architecture"); await settle(page);
  // the diagram is rendered client-side (viz.js) inside the SPA iframe
  const frame = page.frameLocator("iframe").last();
  const svg = frame.locator("#wiki-diagram svg").first();
  await expect(svg).toBeVisible({ timeout: 30000 });
  await expect(svg).toContainText("Public data sources", { timeout: 15000 });
  await page.waitForTimeout(800);
  await page.screenshot({ path: `${SHOTS}wiki_system_architecture.png`, fullPage: true });
});
