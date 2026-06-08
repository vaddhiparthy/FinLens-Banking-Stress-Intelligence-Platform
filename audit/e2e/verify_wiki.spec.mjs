import { test, expect } from "@playwright/test";

const SHOT = "../screenshots";

// #89: the wiki is a client-side SPA — instant nav (no Streamlit rerun per article), a section tree,
// search, and in-app cross-links. The System Architecture article keeps its Streamlit route.
test("wiki SPA renders, tree navigates instantly, search filters", async ({ page }) => {
  await page.goto("/Wiki");
  // the SPA lives in the (tall) components iframe; the first iframe is the height-0 meta tag
  const frame = page.frameLocator("iframe").last();
  // the tree shows section + article leaves
  await expect(frame.locator(".tree-sec", { hasText: "Introduction" })).toBeVisible({ timeout: 20000 });
  await expect(frame.locator(".tree-art").first()).toBeVisible();
  // content pane shows an article title + body
  await expect(frame.locator(".title")).toBeVisible();
  await expect(frame.locator(".body")).toBeVisible();
  await page.screenshot({ path: `${SHOT}/wiki_spa.png`, fullPage: true });

  // click a different article -> content swaps without a Streamlit rerun (URL unchanged)
  const urlBefore = page.url();
  await frame.locator('.tree-art[data-slug="glossary"]').click();
  await expect(frame.locator(".title")).toContainText("Glossary", { timeout: 8000 });
  expect(page.url()).toBe(urlBefore); // no server round-trip / query change

  // search filters the tree
  await frame.locator("#q").fill("calibration");
  await expect(frame.locator(".tree-art:not(.hidden)").first()).toBeVisible({ timeout: 5000 });
  const visible = await frame.locator(".tree-art:not(.hidden)").count();
  const all = await frame.locator(".tree-art").count();
  expect(visible).toBeLessThan(all);
  expect(visible).toBeGreaterThan(0);
});

test("System Architecture renders the interactive diagram inside the SPA", async ({ page }) => {
  await page.goto("/Wiki?article=system-architecture");
  // the diagram is rendered client-side (viz.js) inside the SPA iframe with pan/zoom controls
  const frame = page.frameLocator("iframe").last();
  await expect(frame.locator("#wiki-diagram svg").first()).toBeVisible({ timeout: 30000 });
  await expect(frame.locator("#svg-pan-zoom-controls")).toHaveCount(1, { timeout: 25000 });
});
