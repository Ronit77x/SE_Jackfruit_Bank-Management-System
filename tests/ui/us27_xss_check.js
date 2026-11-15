// Genuine browser XSS/output-encoding regression for the existing Customer UI.
// Run with Playwright available to Node and a local app serving this branch:
//   node tests/ui/us27_xss_check.js
const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  });
  const context = await browser.newContext({
    timezoneId: "America/Los_Angeles",
    viewport: { width: 1280, height: 800 },
  });
  await context.addInitScript(() => {
    sessionStorage.setItem("bms_token", "browser-test-token");
    sessionStorage.setItem("bms_role", "Customer");
    sessionStorage.setItem("bms_must_change", "false");
    sessionStorage.setItem("bms_username", "browser-customer");
  });
  const consoleErrors = [];
  const dialogs = [];
  const page = await context.newPage();
  page.on("console", message => { if (message.type() === "error") { consoleErrors.push(message.text()); } });
  page.on("dialog", dialog => { dialogs.push(dialog.type()); dialog.dismiss(); });
  const hostile = '<img src=x onerror="alert(1)"> <script>alert(2)</script> "quoted"';
  await page.route("**/accounts", route => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ accounts: [{ account_id: 1, account_number: hostile, account_type: hostile, status: "Active", balance: "100.00" }] }),
  }));
  await page.route("**/accounts/by-id/1/transactions*", route => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      transactions: [{ createdAt: "2026-11-15T06:00:00", type: hostile, amount: "1.00", balanceAfter: "99.00", receiptNo: hostile, reference: hostile }],
      count: 1, total: 1, hasMore: false, miniStatement: true,
    }),
  }));
  await page.goto("http://127.0.0.1:8766/ui/customer.html");
  await page.locator("#history-rows tr").waitFor();
  const bodyText = await page.locator("body").innerText();
  if (!bodyText.includes(hostile) || await page.locator("#history-rows img, #history-rows script").count()) {
    throw new Error("Hostile values were not rendered as literal text");
  }
  if (dialogs.length || consoleErrors.length) {
    throw new Error(`Unexpected browser side effects: dialogs=${JSON.stringify(dialogs)}, console=${JSON.stringify(consoleErrors)}`);
  }
  console.log("PASS: hostile account/transaction values rendered as literal text; no dialog or console error");
  await browser.close();
})().catch(error => { console.error(error); process.exitCode = 1; });
