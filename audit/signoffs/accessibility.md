# Ceiling A sign-off: accessibility

VERDICT: PASS

ARTIFACTS REVIEWED:
- audit/e2e/axe-scan.mjs (axe-core runner)
- audit/axe/{home,data_engineering,ai_engineering,analyst_assistant,early_warning}.json (5 pages)
- audit/lighthouse/{home,data_engineering,ai_engineering,analyst_assistant,early_warning}.json (5 pages)
- audit/findings_frontend.md (A-001 popover->expander fix)
- streamlit_app/lib/page_shell.py (surface-nav trigger + set_meta_description)
- streamlit_app/pages/7_AI_Engineering.py (paper/cross-check triggers)

BLOCKING ISSUES: none

NOTES:
1. axe config is legitimate. axe-scan.mjs reads the real axe-core min build, launches Chromium at 1440x900, navigates to each live route on localhost:8501, waits for stApp + the Streamlit status widget to settle (no "running") plus a 1.5s settle, then runs `axe.run(document, ...)` against the top document with `runOnly` tags `wcag2a, wcag2aa, wcag21a, wcag21aa`. Correct tag set, real document, non-trivial. Gate exits non-zero on any serious/critical. Not a rigged config.
2. axe results: 0 violations on all 5 pages, with substantive pass counts (home 23, DE 17, AI 16, assistant 16, early-warning 28). Genuinely 0 serious/critical everywhere.
3. A-001 fix verified. `st.popover` does not appear anywhere in streamlit_app (repo-wide grep: no matches). page_shell.py line 299 uses `st.expander` for the surface-nav trigger; 7_AI_Engineering.py uses `st.expander` for the paper/cross-check/model-card triggers. The original critical aria-allowed-attr is resolved at the source, not patched into a nested-interactive trade-off. Lighthouse aria-allowed-attr scores 1 on every page that carries the a11y category.
4. Meta-injection did not introduce a frame-title violation. set_meta_description injects via a zero-height same-origin components.html iframe. axe reports 0 frame-title violations on all 5 pages, and Lighthouse frame-title scores 1 on all 4 pages that ran the a11y category. No regression.
5. Lighthouse corroborates accessibility = 1.00 (100) on 4 of 5 pages: home, ai_engineering, analyst_assistant, early_warning. Key WCAG audits on those (aria-allowed-attr, color-contrast where applicable, frame-title, label, aria-required-attr, button-name, link-name, image-alt) all pass.
6. Artifact-completeness gap (not a violation): audit/lighthouse/data_engineering.json is a performance-only run. It contains only the `performance` category and carries no accessibility category or accessibility audits. The A-010 ledger entry asserts DE "a11y 100", but that number is not backed by the committed Lighthouse artifact for DE. This does not block: the DE page is covered by the authoritative WCAG tool (axe: 0 violations, 17 passes), and no other artifact reveals a DE a11y defect. Recommend re-running Lighthouse on DE with the accessibility category so the "a11y 100 on all 5" claim is fully evidenced rather than 4-of-5 evidenced.
7. No contrast, label, or ARIA violation found in any artifact. color-contrast is `notApplicable` on home (no scorable text nodes at scan time) and `1` on the other three full runs; label and button/link-name pass throughout.
