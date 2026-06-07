import { test, expect } from "@playwright/test";

const SHOT = "../screenshots";

// Material-icon buttons carry the icon ligature in their accessible name (e.g. "home Home"), so
// target the keyed wrapper classes Streamlit emits (st-key-<key>) instead of role+name.
const menu = (page) => page.getByRole("button", { name: "Menu" });
const homeBtn = (page) => page.locator('[class*="st-key-ham_home"] button');
const chatBtn = (page) => page.locator('[class*="st-key-ham_chat"] button');

// #82: a persistent hamburger (Menu popover) on every page; opening it reveals Home, the group
// sitemaps (each a + expander), and Chat; Home/sub-pages reachable everywhere.
test("hamburger present + opens on home", async ({ page }) => {
  await page.goto("/");
  const gate = page.getByRole("button", { name: "I understand" });
  await gate.click({ timeout: 20000 }).catch(() => {});
  await expect(gate).toBeHidden({ timeout: 10000 }).catch(() => {});
  await expect(menu(page)).toBeVisible({ timeout: 20000 });
  await page.screenshot({ path: `${SHOT}/nav_home_closed.png` });
  await menu(page).click();
  const panel = page.locator('[data-testid="stPopoverBody"]');
  await expect(panel.getByText("Navigation", { exact: true })).toBeVisible({ timeout: 10000 });
  await expect(homeBtn(page)).toBeVisible();
  await expect(panel.getByText("AI Engineering", { exact: true })).toBeVisible();
  await expect(panel.getByText("Data Engineering", { exact: true })).toBeVisible();
  await expect(chatBtn(page)).toBeVisible();
  await page.screenshot({ path: `${SHOT}/nav_home_open.png`, fullPage: true });
});

test("hamburger on a sub-page: group expands and sub-page navigates", async ({ page }) => {
  await page.goto("/Business_Dashboard");
  await expect(menu(page)).toBeVisible({ timeout: 20000 });
  await menu(page).click();
  await page.screenshot({ path: `${SHOT}/nav_subpage_open.png`, fullPage: true });
  await page.getByText("AI Engineering").click();
  const inf = page.getByRole("button", { name: "AI Inference" });
  await expect(inf).toBeVisible({ timeout: 8000 });
  await inf.click();
  await expect(page).toHaveURL(/AI_Inference/, { timeout: 15000 });
});

test("Home reachable from a sub-page via the hamburger", async ({ page }) => {
  await page.goto("/Technical_Dashboard");
  await menu(page).click({ timeout: 20000 });
  await homeBtn(page).click({ timeout: 10000 });
  await expect(page.getByText("Browse the project")).toBeVisible({ timeout: 15000 });
});

// #83: the use-notice shows only on a fresh direct landing; never re-prompts on internal navigation.
test("disclaimer does not re-prompt on internal navigation", async ({ page }) => {
  await page.goto("/");
  const gate = page.getByRole("button", { name: "I understand" });
  await expect(gate).toBeVisible({ timeout: 20000 });  // fresh landing => gate shows once
  await gate.click();
  await expect(gate).toBeHidden({ timeout: 10000 });
  // navigate out to a sub-page and back home via the hamburger
  await menu(page).click();
  await chatBtn(page).click();  // -> AI Inference
  await expect(page).toHaveURL(/AI_Inference/, { timeout: 15000 });
  await menu(page).click();
  await homeBtn(page).click();
  await expect(page.getByText("Browse the project")).toBeVisible({ timeout: 15000 });
  // the gate must NOT reappear on this internal return to home
  await expect(gate).toBeHidden();
});
