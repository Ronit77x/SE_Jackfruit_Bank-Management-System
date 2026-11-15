/* Optional real-browser check. See docs/customer-history-ui.md for isolated setup. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

(async () => {
  const base = process.env.BMS_UI_TEST_URL || "http://127.0.0.1:8769";
  const output = process.env.BMS_UI_EVIDENCE || path.join(require("node:os").tmpdir(), "bms-customer-ui-evidence");
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({ headless: true,
    ...(process.env.BMS_UI_BROWSER ? { executablePath: process.env.BMS_UI_BROWSER } : {}) });
  const results = { browser: browser.version(), checks: [] };
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, acceptDownloads: true });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  async function check(name, fn) { await fn(); results.checks.push(name); }
  async function ready(text) { await page.locator("#history-summary").filter({ hasText: text }).waitFor(); }
  async function range() {
    await page.locator("#date-from").fill("2020-01-01");
    await page.locator("#date-to").fill("2099-12-31");
    await page.locator("#range-button").click();
    await ready("Showing 1–25 of 61");
  }
  try {
    await page.goto(base + "/ui/index.html");
    await page.locator("#username").fill("ui_customer");
    await page.locator("#password").fill("TestPassword123!");
    await page.locator("button[type=submit]").click();
    await page.waitForURL("**/ui/customer.html");
    await ready("Latest 10 of 61");
    await check("real login reaches customer entry, masked accounts and exact money", async () => {
      assert.equal(await page.locator("#history-rows tr").count(), 10);
      const text = await page.locator("main").innerText();
      assert(!text.includes("1234567890")); assert(!text.includes("9876547890"));
      assert(text.includes("Rs 1,23,45,67,89,012.99"));
      assert.equal(await page.locator("#account option").count(), 2);
    });
    await check("all pages navigable with complete totals and boundary buttons", async () => {
      await range(); assert(await page.locator("#previous-button").isDisabled());
      await page.locator("#next-button").click(); await ready("Showing 26–50 of 61");
      await page.locator("#next-button").click(); await ready("Showing 51–61 of 61");
      assert(await page.locator("#next-button").isDisabled());
      await page.locator("#previous-button").click(); await ready("Showing 26–50 of 61");
      await page.screenshot({ path: path.join(output, "desktop.png"), fullPage: true });
    });
    await check("CSV download contains all 61 records rather than the visible page", async () => {
      const pending = page.waitForEvent("download"); await page.locator("#download-button").click();
      const download = await pending; const file = path.join(output, download.suggestedFilename());
      await download.saveAs(file); const csv = fs.readFileSync(file, "utf8");
      assert(csv.includes("Number of transactions,61")); assert(!csv.includes("1234567890"));
      assert.equal((csv.match(/DEMO-/g) || []).length, 61);
      await page.locator("#history-message").filter({ hasText: "CSV downloaded" }).waitFor();
    });
    await check("invalid date order prevented before any request", async () => {
      let calls = 0; const listener = r => { if (r.url().includes("/transactions?")) { calls++; } };
      page.on("request", listener);
      await page.locator("#date-from").fill("2026-02-02"); await page.locator("#date-to").fill("2026-01-01");
      await page.locator("#range-button").click();
      await page.locator("#history-message").filter({ hasText: "From date must" }).waitFor();
      page.off("request", listener); assert.equal(calls, 0);
    });
    await check("360px viewport contains page and scrollable table", async () => {
      await range(); await page.setViewportSize({ width: 360, height: 800 });
      const dims = await page.evaluate(() => ({ viewport: innerWidth, client: document.documentElement.clientWidth,
        scroll: document.documentElement.scrollWidth, table: document.querySelector(".table-wrap").getBoundingClientRect().right }));
      assert(dims.scroll <= dims.client); assert(dims.table <= dims.viewport);
      results.mobile = dims;
      await page.screenshot({ path: path.join(output, "mobile.png"), fullPage: true });
      await page.setViewportSize({ width: 1280, height: 900 });
    });
    await check("account selection resets pagination; frozen account empty state works", async () => {
      await page.locator("#account").selectOption({ index: 1 }); await ready("Latest 0 of 0");
      assert((await page.locator("#account-summary").innerText()).includes("Frozen"));
      assert((await page.locator("#history-rows").innerText()).includes("No transactions"));
      assert(await page.locator("#pagination").isHidden());
      await page.locator("#account").selectOption({ index: 0 }); await ready("Latest 10 of 61");
    });
    await check("failed download surfaces audit error and never saves a file", async () => {
      await range(); let downloads = 0; const listener = () => downloads++;
      page.on("download", listener);
      await page.route("**/statement?*", route => route.fulfill({ status: 503, contentType: "application/json",
        body: JSON.stringify({ code: "STATEMENT_AUDIT_UNAVAILABLE", message: "Statement download is temporarily unavailable. Please try again." }) }));
      await page.locator("#download-button").click();
      await page.locator("#history-message").filter({ hasText: "temporarily unavailable" }).waitFor();
      assert.equal(downloads, 0); page.off("download", listener); await page.unroute("**/statement?*");
    });
    await check("late response from a previous account cannot overwrite the new account", async () => {
      const firstId = await page.locator("#account option").first().getAttribute("value");
      let release;
      const gate = new Promise(resolve => { release = resolve; });
      let intercepted;
      const started = new Promise(resolve => { intercepted = resolve; });
      const pattern = "**/accounts/by-id/" + firstId + "/transactions";
      await page.route(pattern, async route => {
        const response = await route.fetch(); intercepted(); await gate; await route.fulfill({ response });
      });
      await page.locator("#latest-button").click(); await started;
      await page.locator("#account").selectOption({ index: 1 }); await ready("Latest 0 of 0");
      release(); await page.unroute(pattern, { behavior: "wait" });
      assert((await page.locator("#history-summary").innerText()).includes("Latest 0 of 0"));
      assert((await page.locator("#history-rows").innerText()).includes("No transactions"));
      await page.locator("#account").selectOption({ index: 0 }); await ready("Latest 10 of 61");
    });
    await check("server text remains inert and a failed refresh clears stale rows", async () => {
      await page.route("**/transactions", async route => {
        const response = await route.fetch(); const data = await response.json();
        data.transactions[0].reference = '<img src=x onerror="window.injected=true">';
        await route.fulfill({ response, json: data });
      });
      await page.locator("#latest-button").click(); await ready("Latest 10 of 61");
      assert.equal(await page.locator("#history-rows img").count(), 0);
      assert((await page.locator("#history-rows").innerText()).includes("<img"));
      await page.unroute("**/transactions");
      await page.route("**/transactions", route => route.abort());
      await page.locator("#latest-button").click();
      await page.locator("#history-message").filter({ hasText: "Cannot reach" }).waitFor();
      assert.equal(await page.locator("#history-rows tr").count(), 0);
      await page.unroute("**/transactions");
      await page.locator("#latest-button").click(); await ready("Latest 10 of 61");
    });
    await check("401 clears shared session and returns to login", async () => {
      await page.route("**/transactions", route => route.fulfill({ status: 401, contentType: "application/json", body: '{"message":"Session ended"}' }));
      await page.locator("#latest-button").click(); await page.waitForURL("**/ui/index.html?expired=1");
      assert.equal(await page.evaluate(() => sessionStorage.getItem("bms_token")), null);
    });
    await check("customer with no accounts sees a useful empty state", async () => {
      await page.locator("#username").fill("ui_empty"); await page.locator("#password").fill("TestPassword123!");
      await page.locator("button[type=submit]").click(); await page.waitForURL("**/ui/customer.html");
      await page.locator("#account-message").filter({ hasText: "no accounts yet" }).waitFor();
      assert(await page.locator("#activity").isHidden());
    });
    assert.deepEqual(errors, []);
    fs.writeFileSync(path.join(output, "browser-results.json"), JSON.stringify(results, null, 2));
    console.log(JSON.stringify(results, null, 2));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
