import { test } from "@playwright/test";
const S = new URL("../screenshots/v2/", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
async function settle(p){await p.waitForSelector('[data-testid="stApp"]',{timeout:30000});await p.waitForFunction(()=>{const r=document.querySelector('[data-testid="stStatusWidget"]');return !r||!/running/i.test(r.textContent||"");},{timeout:30000}).catch(()=>{});await p.waitForTimeout(1200);}
test("ai_inference_populated", async ({ page }) => {
  test.setTimeout(150000);
  await page.goto("/AI_Inference"); await settle(page);
  const i=page.getByPlaceholder(/Ask a question/i);
  await i.fill("What happened to Silicon Valley Bank?"); await i.press("Enter");
  await page.getByText(/FDIC CERT/i).first().waitFor({timeout:120000}).catch(()=>{});
  await page.waitForTimeout(1500);
  await page.screenshot({path:`${S}ai_inference.png`,fullPage:true});
});
