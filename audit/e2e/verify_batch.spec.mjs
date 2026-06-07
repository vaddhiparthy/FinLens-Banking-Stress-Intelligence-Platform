import { test, expect } from "@playwright/test";

const SHOT = "../screenshots";

async function dismissGate(page) {
  const btn = page.getByRole("button", { name: "I understand" });
  if (await btn.isVisible().catch(() => false)) await btn.click();
}

test("home batch capture", async ({ page }) => {
  await page.goto("/");
  await dismissGate(page);
  await expect(page.getByText("Browse the project")).toBeVisible({ timeout: 20000 });
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${SHOT}/batch_home.png`, fullPage: true });
});

test("business dashboard capture + blank-fix", async ({ page }) => {
  await page.goto("/Business_Dashboard");
  const charts = page.locator('[data-testid="stPlotlyChart"]');
  await expect.poll(async () => charts.count(), { timeout: 30000 }).toBeGreaterThanOrEqual(4);
  // the margin/unrealized slot must NOT read as dead space, and must show the NIM substitute
  await expect(page.getByText("Margin and unrealized-loss data unavailable.")).toHaveCount(0);
  await expect(page.getByText("Net interest margin (industry)")).toBeVisible();
  await page.waitForTimeout(800);
  await page.screenshot({ path: `${SHOT}/batch_business.png`, fullPage: true });
});

test("technical dashboard capture", async ({ page }) => {
  await page.goto("/Technical_Dashboard");
  await page.waitForTimeout(3500);
  await page.screenshot({ path: `${SHOT}/batch_technical.png`, fullPage: true });
});

test("ai inference capture", async ({ page }) => {
  await page.goto("/AI_Inference");
  await page.waitForTimeout(2000);
  const input = page.getByPlaceholder("Ask a question");
  await input.fill("Why did Silicon Valley Bank fail?");
  await input.press("Enter");
  await page.waitForTimeout(9000);
  await page.screenshot({ path: `${SHOT}/batch_ai_inference.png`, fullPage: true });
});
