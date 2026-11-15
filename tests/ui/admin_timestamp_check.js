// Genuine browser regression for the Admin audit timestamp contract.
// Run with Playwright available to Node and a local app serving this branch:
//   node tests/ui/admin_timestamp_check.js
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
  const page = await context.newPage();
  await page.route("**/admin/audit-logs*", route => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify([
      { id: 1, timestamp: "2026-11-15T06:00:00", user_id: 1, action: "NAIVE", outcome: "SUCCESS", details: "naive" },
      { id: 2, timestamp: "2026-11-15T06:00:00Z", user_id: 1, action: "UTC", outcome: "SUCCESS", details: "explicit" },
      { id: 3, timestamp: "2026-11-15T06:00:00+05:30", user_id: 1, action: "IST", outcome: "SUCCESS", details: "offset-positive" },
      { id: 4, timestamp: "2026-11-15T06:00:00-04:00", user_id: 1, action: "EDT", outcome: "SUCCESS", details: "offset-negative" },
      { id: 5, timestamp: "not-a-timestamp", user_id: 1, action: "BAD", outcome: "SUCCESS", details: "malformed" },
    ]),
  }));
  await page.goto("http://127.0.0.1:8765/ui/admin.html");
  await page.locator("#audit-form button").click();
  await page.locator("#audit-table tbody tr").nth(4).waitFor();
  const times = await page.locator("#audit-table tbody tr td:first-child").allTextContents();
  const expected = [
    "2026-11-15 11:30 IST",
    "2026-11-15 11:30 IST",
    "2026-11-15 06:00 IST",
    "2026-11-15 15:30 IST",
    "Invalid timestamp",
  ];
  if (JSON.stringify(times) !== JSON.stringify(expected)) {
    throw new Error(`Unexpected audit timestamp rendering: ${JSON.stringify(times)}`);
  }
  if (!(await page.locator("th", { hasText: "Time (IST)" }).count())) {
    throw new Error("IST table heading is missing");
  }
  if (!(await page.locator("label", { hasText: "From date (IST)" }).count()) ||
      !(await page.locator("label", { hasText: "To date (IST)" }).count())) {
    throw new Error("IST date-filter labels are missing");
  }
  expected.forEach((value, index) => console.log(`PASS case ${index + 1}: ${times[index]} (expected ${value})`));
  await browser.close();
})().catch(error => { console.error(error); process.exitCode = 1; });
