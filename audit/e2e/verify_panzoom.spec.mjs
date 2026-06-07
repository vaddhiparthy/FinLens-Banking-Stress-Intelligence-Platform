import { test, expect } from "@playwright/test";

// #88: the architecture diagram must get the svg-pan-zoom overlay (scroll zoom, drag pan, controls).
test("architecture diagram has pan/zoom controls attached", async ({ page }) => {
  await page.goto("/Wiki?article=system-architecture");
  // graphviz renders the svg first
  const svg = page.locator('[data-testid="stGraphVizChart"] svg').first();
  await expect(svg).toBeVisible({ timeout: 30000 });
  // svg-pan-zoom marks the svg and injects a controls group once it initialises
  await expect(svg).toHaveAttribute("data-panzoom", "1", { timeout: 25000 });
  await expect(page.locator("#svg-pan-zoom-controls")).toHaveCount(1, { timeout: 25000 });
});
