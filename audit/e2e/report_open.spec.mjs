import { test, expect } from "@playwright/test";

async function settle(page) {
  await page.waitForSelector('[data-testid="stApp"]', { timeout: 30_000 });
  await page.waitForFunction(() => {
    const r = document.querySelector('[data-testid="stStatusWidget"]');
    return !r || !/running/i.test(r.textContent || "");
  }, { timeout: 30_000 }).catch(() => {});
  await page.waitForTimeout(1200);
}

test("chat -> open full report navigates to the report for that bank", async ({ page }) => {
  await page.goto("/AI_Engineering");
  await settle(page);
  await page.getByRole("button", { name: "Research a bank" }).click();
  await settle(page);
  const panel = page.locator(".st-key-finlens_chat_open");
  const input = page.getByPlaceholder(/Ask a question/i);
  await input.fill("SVB");
  await input.press("Enter");
  await settle(page);
  const reportBtn = panel.getByRole("button", { name: /full report on SILICON VALLEY BANK/i });
  await expect(reportBtn).toBeVisible();
  await reportBtn.click();
  await settle(page);
  // Should land on the Bank Report page, showing SVB.
  await expect(page).toHaveURL(/Bank_Report/i, { timeout: 30_000 });
  await expect(page.getByText("Bank Distress Report").first()).toBeVisible();
  await expect(page.getByText(/SILICON VALLEY BANK/i).first()).toBeVisible();
});
