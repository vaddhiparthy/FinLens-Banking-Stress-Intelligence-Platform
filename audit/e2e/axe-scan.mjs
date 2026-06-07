// Re-run axe-core against the live app after the Ceiling-A DOM changes (active-tab pill,
// AI flow diagram, expanders, injected meta). Writes one JSON per page to audit/axe/.
import { chromium } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const axeSrc = fs.readFileSync(
  path.join(here, "..", "..", "node_modules", "axe-core", "axe.min.js"), "utf8");
const outDir = path.join(here, "..", "axe");
fs.mkdirSync(outDir, { recursive: true });

const PAGES = [
  ["home", "/"],
  ["data_engineering", "/Data_Engineering"],
  ["ai_engineering", "/AI_Engineering"],
  ["analyst_assistant", "/Analyst_Assistant"],
  ["early_warning", "/Early_Warning"],
];

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
let total = 0;
for (const [name, route] of PAGES) {
  const page = await ctx.newPage();
  await page.goto("http://localhost:8501" + route, { waitUntil: "load" });
  await page.waitForSelector('[data-testid="stApp"]', { timeout: 30000 });
  await page.waitForFunction(() => {
    const r = document.querySelector('[data-testid="stStatusWidget"]');
    return !r || !/running/i.test(r.textContent || "");
  }, { timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(1500);
  await page.evaluate(axeSrc);
  const results = await page.evaluate(async () => {
    // Scan the top document; serious/critical impacts only matter for the gate.
    return await window.axe.run(document, {
      runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"] },
    });
  });
  const violations = results.violations.map((v) => ({
    id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.length,
  }));
  fs.writeFileSync(
    path.join(outDir, name + ".json"),
    JSON.stringify({ url: route, nViolations: results.violations.length, violations,
                     passes: results.passes.length }, null, 2));
  const crit = results.violations.filter((v) => ["serious", "critical"].includes(v.impact));
  console.log(`${name}: ${results.violations.length} violations (${crit.length} serious/critical)`);
  total += crit.length;
  await page.close();
}
await browser.close();
console.log(`TOTAL serious/critical: ${total}`);
process.exit(total > 0 ? 1 : 0);
