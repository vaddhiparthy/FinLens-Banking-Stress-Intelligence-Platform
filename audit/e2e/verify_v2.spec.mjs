import { test } from "@playwright/test";
import fs from "node:fs";
const S = new URL("../screenshots/v2/", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
fs.mkdirSync(S, { recursive: true });
async function settle(p){await p.waitForSelector('[data-testid="stApp"]',{timeout:30000});await p.waitForFunction(()=>{const r=document.querySelector('[data-testid="stStatusWidget"]');return !r||!/running/i.test(r.textContent||"");},{timeout:30000}).catch(()=>{});await p.waitForTimeout(1400);}
async function ack(p){const b=p.getByRole("button",{name:"I understand"});await b.waitFor({state:"visible",timeout:8000}).catch(()=>{});if(await b.isVisible().catch(()=>false)){await b.click();await b.waitFor({state:"detached",timeout:10000}).catch(()=>{});await settle(p);}}
const FULL={fullPage:true};
test("home", async ({ page }) => { await page.goto("/"); await settle(page); await ack(page); await page.getByText("Browse the project").first().waitFor({timeout:30000}); await page.waitForTimeout(600); await page.screenshot({path:`${S}home.png`,...FULL}); });
test("ai_inference", async ({ page }) => { await page.goto("/AI_Inference"); await settle(page); const i=page.getByPlaceholder(/Ask a question/i); await i.fill("What happened to Silicon Valley Bank?"); await i.press("Enter"); await settle(page); await page.waitForTimeout(1500); await page.screenshot({path:`${S}ai_inference.png`,...FULL}); });
test("business_dashboard", async ({ page }) => { await page.goto("/Business_Dashboard"); await settle(page); await page.waitForFunction(()=>document.querySelectorAll(".js-plotly-plot").length>=2,{timeout:30000}).catch(()=>{}); await page.waitForTimeout(800); await page.screenshot({path:`${S}business_dashboard.png`,...FULL}); });
test("technical_dashboard", async ({ page }) => { await page.goto("/Technical_Dashboard"); await settle(page); await page.waitForFunction(()=>document.querySelectorAll(".js-plotly-plot").length>=2,{timeout:30000}).catch(()=>{}); await page.waitForTimeout(800); await page.screenshot({path:`${S}technical_dashboard.png`,...FULL}); });
