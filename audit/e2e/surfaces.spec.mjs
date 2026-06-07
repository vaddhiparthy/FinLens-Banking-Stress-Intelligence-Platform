import { test, expect } from "@playwright/test";
import fs from "node:fs";

const SHOTS = new URL("../screenshots/", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
fs.mkdirSync(SHOTS, { recursive: true });

// Streamlit renders over a websocket, so "load" fires before content exists. Wait for the
// app shell, let the run settle, and assert on real text instead of network idle.
async function settle(page) {
  await page.waitForSelector('[data-testid="stApp"]', { timeout: 30_000 });
  // Streamlit shows a "Running..." status while a script executes; wait for it to clear.
  await page.waitForFunction(() => {
    const r = document.querySelector('[data-testid="stStatusWidget"]');
    return !r || !/running/i.test(r.textContent || "");
  }, { timeout: 30_000 }).catch(() => {});
  await page.waitForTimeout(1200);
}

async function shot(page, name) {
  await page.screenshot({ path: `${SHOTS}${name}.png`, fullPage: false });
}

test("home surface renders the brand and entry", async ({ page }) => {
  await page.goto("/");
  await settle(page);
  await expect(page.getByText("FinLens").first()).toBeVisible();
  await shot(page, "e2e_home");
});

test("data engineering surface renders the live pipeline", async ({ page }) => {
  await page.goto("/Data_Engineering");
  await settle(page);
  await expect(page.getByText("Live Pipeline").first()).toBeVisible();
  await shot(page, "e2e_de_pipeline");
});

test("data engineering Data Quality shows the GX suite result", async ({ page }) => {
  await page.goto("/Data_Engineering");
  await settle(page);
  await page.getByRole("button", { name: "Data Quality" }).first().click();
  await settle(page);
  await expect(page.getByText("Great Expectations Suite").first()).toBeVisible();
  await shot(page, "e2e_de_quality_gx");
});

test("AI surface renders the model pipeline flow", async ({ page }) => {
  await page.goto("/AI_Engineering");
  await settle(page);
  await expect(page.getByText("Training & scoring pipeline").first()).toBeVisible();
  // The flow diagram stages should be present.
  await expect(page.getByText("Serve + monitor").first()).toBeVisible();
  await shot(page, "e2e_ai_pipeline");
});

test("AI Model Quality shows the headline metrics and robustness cross-checks", async ({ page }) => {
  await page.goto("/AI_Engineering");
  await settle(page);
  await page.getByRole("button", { name: "Model Quality" }).first().click();
  await settle(page);
  await expect(page.getByText("PR-AUC (OOT)").first()).toBeVisible();
  await expect(page.getByText("Robustness & validation cross-checks").first()).toBeVisible();
  await shot(page, "e2e_ai_quality");
});

test("AI Decisions surface exposes the methodology write-ups", async ({ page }) => {
  await page.goto("/AI_Engineering");
  await settle(page);
  await page.getByRole("button", { name: "Decisions" }).first().click();
  await settle(page);
  await expect(page.getByText("Methodology write-ups").first()).toBeVisible();
  await shot(page, "e2e_ai_decisions");
});

test("analyst assistant renders a cited cached answer", async ({ page }) => {
  await page.goto("/Analyst_Assistant");
  await settle(page);
  await expect(page.getByText("Analyst Assistant").first()).toBeVisible();
  // A cached demonstration answer renders without invoking the live model.
  await expect(page.getByText("Answer").first()).toBeVisible();
  // The live-ask affordance exists.
  await expect(page.getByRole("button", { name: "Ask live" })).toBeVisible();
  await shot(page, "e2e_assistant");
});

test("early warning surface renders", async ({ page }) => {
  await page.goto("/Early_Warning");
  await settle(page);
  await expect(page.getByText(/Early Warning/i).first()).toBeVisible();
  await shot(page, "e2e_early_warning");
});
