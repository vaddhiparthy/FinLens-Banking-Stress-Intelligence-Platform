import { test, expect } from "@playwright/test";
async function settle(p){await p.waitForSelector('[data-testid="stApp"]',{timeout:30000});await p.waitForFunction(()=>{const r=document.querySelector('[data-testid="stStatusWidget"]');return !r||!/running/i.test(r.textContent||"");},{timeout:30000}).catch(()=>{});await p.waitForTimeout(1500);}
test("architecture diagram nodes carry hover tooltips (xlink:title)", async ({ page }) => {
  await page.goto("/Wiki?article=system-architecture"); await settle(page);
  await page.waitForFunction(()=>[...document.querySelectorAll("svg")].some(s=>/Public data sources/.test(s.textContent||"")),{timeout:30000});
  const info = await page.evaluate(()=>{
    const svg=[...document.querySelectorAll("svg")].find(s=>/Public data sources/.test(s.textContent||""));
    const links=[...svg.querySelectorAll("a")];
    const tips=links.map(a=>a.getAttribute("xlink:title")||a.getAttributeNS("http://www.w3.org/1999/xlink","title")||"").filter(Boolean);
    return {count: tips.length, hasDetail: tips.some(t=>/Hive-partitioned|rotation policy|warehouse of record|Turnstile/i.test(t))};
  });
  expect(info.count).toBeGreaterThanOrEqual(20);
  expect(info.hasDetail).toBe(true);
});
