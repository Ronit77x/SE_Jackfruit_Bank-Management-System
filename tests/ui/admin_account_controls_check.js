// Genuine browser smoke/regression check for Admin account-status controls.
// Run with Playwright available to Node and a local app serving this branch:
//   node tests/ui/admin_account_controls_check.js
const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  });
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  await context.addInitScript(() => {
    sessionStorage.setItem("bms_token", "browser-test-token");
    sessionStorage.setItem("bms_role", "Admin");
    sessionStorage.setItem("bms_must_change", "false");
    sessionStorage.setItem("bms_username", "browser-admin");
  });
  const page = await context.newPage();
  const requests = [];
  page.on("request", request => { if (request.method() === "PATCH") { requests.push(request.postDataJSON()); } });
  let dismissClose = true;
  page.on("dialog", dialog => { if (dismissClose) { dialog.dismiss(); } else { dialog.accept(); } });
  await page.route("**/accounts/*/status", route => {
    if (route.request().url().includes("9999999999")) {
      return route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: '<script>alert(1)</script> Account not found' }) });
    }
    const action = route.request().postDataJSON().action;
    const status = { freeze: "Frozen", unfreeze: "Active", close: "Closed" }[action];
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ id: 1, account_number: "1000000001", status, balance: "0.00", type: "Savings" }) });
  });
  await page.goto("http://127.0.0.1:8768/ui/admin.html");
  await page.locator("#account-identifier").fill("1000000001");
  await page.locator("button[data-status-action=close]").click();
  await page.waitForTimeout(100);
  if (requests.length) { throw new Error("Close was submitted after confirmation was dismissed"); }
  await page.locator("button[data-status-action=freeze]").click();
  await page.locator("#account-status-message").waitFor();
  if (!requests.length || requests[0].action !== "freeze" || !(await page.locator("#account-status-message").textContent()).includes("Frozen")) {
    throw new Error("Freeze action did not submit or render success");
  }
  await page.locator("#account-identifier").fill("1000000001");
  await page.locator("button[data-status-action=unfreeze]").click();
  await page.locator("#account-status-message").waitFor();
  if (requests[1].action !== "unfreeze" || !(await page.locator("#account-status-message").textContent()).includes("Active")) {
    throw new Error("Unfreeze action did not submit or render success");
  }
  dismissClose = false;
  await page.locator("#account-identifier").fill("1000000001");
  await page.locator("button[data-status-action=close]").click();
  await page.locator("#account-status-message").waitFor();
  if (requests[2].action !== "close" || !(await page.locator("#account-status-message").textContent()).includes("Closed")) {
    throw new Error("Close action did not submit or render success");
  }
  await page.locator("#account-identifier").fill("9999999999");
  await page.locator("button[data-status-action=unfreeze]").click();
  await page.locator("#account-status-message").waitFor();
  const errorText = await page.locator("#account-status-message").textContent();
  if (!errorText.includes("<script>alert(1)</script>") || await page.locator("#account-status-message script").count()) {
    throw new Error("Hostile account-status error was not rendered as literal text");
  }
  await page.setViewportSize({ width: 360, height: 800 });
  if (await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)) {
    throw new Error("Mobile Admin account-controls page overflows horizontally");
  }
  console.log("PASS: close confirmation, freeze action, safe error rendering and mobile layout");
  await browser.close();
})().catch(error => { console.error(error); process.exitCode = 1; });
