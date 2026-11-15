// Genuine browser XSS/output-encoding regression for the merged Admin audit UI.
// Run with Playwright available to Node and a local app serving this branch:
//   node tests/ui/us27_admin_audit_xss_check.js
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
    sessionStorage.setItem("bms_role", "Admin");
    sessionStorage.setItem("bms_must_change", "false");
    sessionStorage.setItem("bms_username", "browser-admin");
  });
  const consoleErrors = [];
  const dialogs = [];
  const page = await context.newPage();
  page.on("console", message => { if (message.type() === "error") { consoleErrors.push(message.text()); } });
  page.on("dialog", dialog => { dialogs.push(dialog.type()); dialog.dismiss(); });
  const hostile = {
    action: '<svg onload="alert(1)">ACTION</svg>',
    details: '<img src=x onerror="alert(2)"><script>alert(3)</script> & "quoted"',
  };
  await page.route("**/admin/audit-logs*", route => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify([
      { id: 1, timestamp: "2026-11-15T06:00:00Z", user_id: 1, action: hostile.action, outcome: "SUCCESS", details: hostile.details },
      { id: 2, timestamp: "2026-11-15T06:01:00Z", user_id: null, action: "NORMAL_ACTION", outcome: "FAILURE", details: "Normal audit detail" },
    ]),
  }));
  await page.goto("http://127.0.0.1:8767/ui/admin.html");
  await page.locator("#audit-form button").click();
  await page.locator("#audit-table tbody tr").nth(1).waitFor();
  const tableText = await page.locator("#audit-table").innerText();
  const expectedText = `${hostile.action}\tSUCCESS\t${hostile.details}`;
  if (!tableText.includes(expectedText) || !tableText.includes("Normal audit detail")) {
    throw new Error("Audit values were not rendered as literal text");
  }
  if (await page.locator("#audit-table img, #audit-table script, #audit-table svg").count()) {
    throw new Error("Injected HTML elements appeared inside the audit table");
  }
  if (dialogs.length || consoleErrors.length) {
    throw new Error(`Unexpected browser side effects: dialogs=${JSON.stringify(dialogs)}, console=${JSON.stringify(consoleErrors)}`);
  }
  console.log("PASS: hostile audit action/details rendered literally; normal row rendered; no injected elements, dialogs or console errors");
  await browser.close();
})().catch(error => { console.error(error); process.exitCode = 1; });
