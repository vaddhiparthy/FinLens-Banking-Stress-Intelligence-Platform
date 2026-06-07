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

test("wiki System Architecture renders the graphviz diagram", async ({ page }) => {
  await page.goto("/Wiki?article=system-architecture"); await settle(page);
  await expect(page.getByText("System Architecture").first()).toBeVisible({ timeout: 30000 });
  // the graphviz chart renders an <svg> carrying the cluster labels (scan ALL svgs, not the
  // first icon svg)
  await page.waitForFunction(
    () => [...document.querySelectorAll("svg")].some(
      (s) => /Public data sources/.test(s.textContent || "")),
    { timeout: 30000 }
  );
  await page.waitForTimeout(800);
  await page.screenshot({ path: `${SHOTS}wiki_system_architecture.png`, fullPage: true });
  // close-up of just the diagram so its readability can be judged
  const chart = page.locator('[data-testid="stGraphVizChart"]').first();
  await chart.scrollIntoViewIfNeeded();
  await chart.screenshot({ path: `${SHOTS}wiki_diagram_closeup.png` });
});
