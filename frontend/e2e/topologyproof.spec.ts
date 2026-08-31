import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
const fixture = path.resolve("e2e/.fixture");
test.beforeAll(() => { if (!fs.existsSync(path.join(fixture,".git"))) execFileSync("python", ["-m", "demo.webhook_dedup.materialize", "--destination", fixture], { cwd: ".." }); });
test("real desktop analysis flow", async ({ page }) => {
 const errors:string[]=[]; page.on("response", _r=>{}); page.on("pageerror", e=>errors.push(e.message)); page.on("console", m=>{if(m.type()==="error" && !m.text().includes("404")) errors.push(m.text());});
 await page.goto("/"); await expect(page.getByText("TopologyProof")).toBeVisible();
 const base=execFileSync("git",["-C",fixture,"rev-parse","HEAD~1"],{encoding:"utf8",cwd:".."}).trim(); const candidate=execFileSync("git",["-C",fixture,"rev-parse","HEAD"],{encoding:"utf8",cwd:".."}).trim(); const values=[fixture,"Webhook deduplication must prevent duplicate payments",base,candidate];
 for (let i=0;i<4;i++) await page.locator("input").nth(i).fill(values[i]);
 const post=page.waitForResponse(r=>r.url().endsWith("/api/v1/analyses")&&r.request().method()==="POST"); await page.getByRole("button",{name:"ANALYZE PATCH"}).click(); expect((await post).status()).toBe(202);
 await expect(page.getByText("REVIEW REQUIRED")).toBeVisible({timeout:60000}); await expect(page.getByText("HIGH RISK")).toBeVisible(); await expect(page.getByText("Replica Count")).toBeVisible(); await expect(page.getByText("Request Routing")).toBeVisible(); await page.getByRole("button",{name:"View finding"}).click(); await expect.poll(async()=>page.locator("body").innerText()).toContain("processed_events"); await expect.poll(async()=>page.locator("body").innerText()).toContain("NOT EXECUTED"); await expect(page.getByRole("button",{name:"RUN VERIFICATION"})).toHaveCount(0); await expect(page.getByText("TOPOLOGY-SENSITIVE CORRECTNESS RISK")).toHaveCount(0); expect(errors).toEqual([]);
});










