import { defineConfig } from "@playwright/test";

// Ceiling-A end-to-end suite. Drives the live Streamlit app at :8501, asserts every
// audited surface renders its real content, exercises interactive section navigation and
// the Analyst Assistant chatbot, and emits JUnit XML for the audit ledger.
export default defineConfig({
  testDir: ".",
  testMatch: /(surfaces|chat_report|capture_ceiling|report_open|functional_sweep|verify_changes|verify_diagram|verify_v2|verify_inf|verify_tip)\.spec\.mjs/,
  timeout: 90_000,
  expect: { timeout: 30_000 },
  retries: 1,
  workers: 1,
  reporter: [
    ["list"],
    ["junit", { outputFile: "../playwright/results.xml" }],
  ],
  use: {
    baseURL: "http://localhost:8501",
    viewport: { width: 1440, height: 900 },
    screenshot: "only-on-failure",
    actionTimeout: 20_000,
  },
});
