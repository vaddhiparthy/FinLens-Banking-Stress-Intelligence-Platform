import { test, expect } from "@playwright/test";

async function settle(page) {
  await page.waitForSelector('[data-testid="stApp"]', { timeout: 30_000 });
  await page.waitForFunction(() => {
    const r = document.querySelector('[data-testid="stStatusWidget"]');
    return !r || !/running/i.test(r.textContent || "");
  }, { timeout: 30_000 }).catch(() => {});
  await page.waitForTimeout(1000);
}
async function ack(page) {
  const b = page.getByRole("button", { name: "I understand" });
  if (await b.isVisible().catch(() => false)) { await b.click(); await settle(page); }
}
async function openChat(page) {
  await page.goto("/AI_Engineering"); await settle(page);
  await page.getByRole("button", { name: "Research a bank" }).click(); await settle(page);
  return page.locator(".st-key-finlens_chat_open");
}
async function askChat(page, panel, q) {
  const input = page.getByPlaceholder(/Ask a question/i);
  await input.fill(q); await input.press("Enter"); await settle(page);
  await page.waitForTimeout(800);
}

// ---- Data Engineering: every section tab routes to its own content ----
const DE_SECTIONS = [
  ["Live Pipeline", /Run status by flow/i],
  ["Data Quality", /Great Expectations Suite/i],
  ["Source Contracts", /Source Classification/i],
  ["Engineering Stack", /Platform Stack Readiness/i],
  ["Architecture Decisions", /Architecture/i],
];
for (const [tab, marker] of DE_SECTIONS) {
  test(`DE section "${tab}" renders its content`, async ({ page }) => {
    await page.goto("/Data_Engineering"); await settle(page);
    const btn = page.getByRole("button", { name: tab, exact: false }).first();
    if (await btn.isEnabled()) { await btn.click(); await settle(page); }  // default tab is disabled
    await expect(page.getByText(marker).first()).toBeVisible();
  });
}

// ---- AI Engineering: every section tab routes to its own content ----
const AI_SECTIONS = [
  ["AI Pipeline", /Training & scoring pipeline/i],
  ["Feature Contracts", /Feature contract/i],
  ["AI Stack", /ML stack/i],
  ["Model Quality", /PR-AUC \(OOT\)/i],
  ["Model Decisions", /Key model decisions/i],
];
for (const [tab, marker] of AI_SECTIONS) {
  test(`AI section "${tab}" renders its content`, async ({ page }) => {
    await page.goto("/AI_Engineering"); await settle(page);
    const btn = page.getByRole("button", { name: tab, exact: false }).first();
    if (await btn.isEnabled()) { await btn.click(); await settle(page); }  // default tab is disabled
    await expect(page.getByText(marker).first()).toBeVisible();
  });
}

// ---- Early Warning: what-if slider actually moves the score ----
test("Early Warning what-if: moving a lever changes the probability", async ({ page }) => {
  await page.goto("/Early_Warning"); await settle(page);
  await page.getByRole("tab", { name: /Hypothetical what-if/i }).click(); await settle(page);
  await page.locator('[data-testid="stSlider"]').first().waitFor({ timeout: 30000 });
  // what-if is the LAST tab, so its score text is the last occurrence in the DOM
  const score = page.getByText(/distress within four/i).last();
  const before = await score.innerText();
  // drag the NONCURRENT-loans lever (risk-raising) to its far right; identify it by label,
  // not DOM index (the 3-column layout reorders sliders)
  const thumb = page.locator('[data-testid="stSlider"]').filter({ hasText: /noncurrent/i })
    .first().locator('[role="slider"]');
  const box = await thumb.boundingBox();
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + 400, box.y + box.height / 2, { steps: 14 });
  await page.mouse.up();
  await settle(page);
  await expect(async () => {
    expect(await score.innerText()).not.toEqual(before);
  }).toPass({ timeout: 15000 });
});

// ---- Chat: typo, operating, failed, methodology, nonsense ----
test("chat: typo resolves (fifth thord -> Fifth Third)", async ({ page }) => {
  const panel = await openChat(page);
  await askChat(page, panel, "tell me about fifth thord bank");
  await expect(panel.getByText(/FIFTH THIRD/i).first()).toBeVisible();
});
test("chat: operating bank reads as operating", async ({ page }) => {
  const panel = await openChat(page);
  await askChat(page, panel, "tell me about Comerica Bank");
  await expect(panel.getByText(/operating institution/i).first()).toBeVisible();
});
test("chat: failed bank reads as failed (not safe)", async ({ page }) => {
  const panel = await openChat(page);
  await askChat(page, panel, "what happened to Silicon Valley Bank");
  await expect(panel.getByText(/failed in 2023/i).first()).toBeVisible();
});
test("chat: nonsense does not crash and gives a response", async ({ page }) => {
  test.setTimeout(150_000);  // a non-bank query routes to the local LLM (~30-60s)
  const panel = await openChat(page);
  const input = page.getByPlaceholder(/Ask a question/i);
  await input.fill("asdfqwer zzxx"); await input.press("Enter");
  // wait for the cycle to complete (the user message is echoed once the backend returns)
  await panel.getByText(/asdfqwer zzxx/i).first().waitFor({ timeout: 120_000 });
  await expect(panel.getByText(/Traceback \(most recent|\.py\", line/i)).toHaveCount(0);
});

// ---- Bank report: failed bank shows the reconciliation, operating does not ----
test("bank report: failed bank shows the failed-but-low reconciliation", async ({ page }) => {
  await page.goto("/Bank_Report"); await settle(page);
  const combo = page.locator('[data-testid="stSelectbox"]').first();
  await combo.click(); await page.waitForTimeout(400);
  await page.keyboard.type("Silicon Valley"); await page.waitForTimeout(700);
  await page.keyboard.press("Enter"); await settle(page);
  await expect(page.getByText(/This bank failed, yet the model scored it low/i).first()).toBeVisible();
});

// ---- Wiki: article renders and search filters ----
test("wiki: article renders real content", async ({ page }) => {
  await page.goto("/Wiki?article=out-of-time-evaluation"); await settle(page);
  await expect(page.getByText("The embargo").first()).toBeVisible();
});
