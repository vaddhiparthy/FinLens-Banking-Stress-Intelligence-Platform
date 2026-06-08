import { test, expect } from "@playwright/test";

// #88: the architecture diagram (now rendered client-side in the wiki SPA) must get the
// svg-pan-zoom overlay (scroll zoom, drag pan, on-diagram controls).
test("architecture diagram has pan/zoom controls attached", async ({ page }) => {
  await page.goto("/Wiki?article=system-architecture");
  const frame = page.frameLocator("iframe").last();
  const svg = frame.locator("#wiki-diagram svg").first();
  await expect(svg).toBeVisible({ timeout: 30000 });
  // svg-pan-zoom injects a controls group once it initialises
  await expect(frame.locator("#svg-pan-zoom-controls")).toHaveCount(1, { timeout: 25000 });
});
