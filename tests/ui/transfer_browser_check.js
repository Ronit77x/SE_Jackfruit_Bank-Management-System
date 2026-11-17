/* Rendered browser regression test for Customer Fund Transfer UI (US-14 / BMS-NF-004 / BMS-NF-006). */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");

// Resolve playwright (from standard node_modules or known local runtime paths)
let playwright;
try {
  playwright = require("playwright");
} catch (e) {
  const candidate = "C:\\Users\\HP ELITEBOOK 840 G6\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\node\\node_modules\\playwright";
  if (fs.existsSync(candidate)) {
    playwright = require(candidate);
  } else {
    throw e;
  }
}
const { chromium } = playwright;

// Find browser executable
const candidateBrowsers = [
  process.env.BMS_UI_BROWSER,
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
  "/usr/bin/chromium-browser",
  "/usr/bin/microsoft-edge",
].filter(Boolean);

const executablePath = candidateBrowsers.find((p) => {
  try { return fs.existsSync(p); } catch { return false; }
});

const ROOT = path.resolve(__dirname, "..", "..");
const STATIC = path.join(ROOT, "app", "static");

let serverTransferCount = 0;

// Static HTTP server for UI assets and mocked backend routes
function createTestServer() {
  return http.createServer((req, res) => {
    const reqPath = req.url.split("?")[0];

    // Mock API endpoints
    if (reqPath === "/accounts/me") {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify([
        {
          id: 1,
          accountNumber: "1000000001",
          maskedAccountNumber: "******0001",
          type: "Savings",
          status: "Active",
          balance: "10000.00"
        },
        {
          id: 2,
          accountNumber: "1000000002",
          maskedAccountNumber: "******0002",
          type: "Current",
          status: "Active",
          balance: "25000.00"
        },
        {
          id: 3,
          accountNumber: "1000000099",
          maskedAccountNumber: "******0099",
          type: "Savings",
          status: "Frozen",
          balance: "2000.00"
        }
      ]));
      return;
    }

    if (reqPath === "/transactions/transfer" && req.method === "POST") {
      serverTransferCount++;
      let body = "";
      req.on("data", (chunk) => { body += chunk; });
      req.on("end", () => {
        const parsed = JSON.parse(body || "{}");
        if (parsed.toAccount === "9999999999") {
          res.writeHead(404, { "Content-Type": "application/json" });
          res.end(JSON.stringify({
            code: "ACCOUNT_NOT_FOUND",
            message: "The recipient account was not found. Please double-check the 10-digit account number."
          }));
          return;
        }
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({
          status: "SUCCESS",
          transactionId: 101,
          reference: "TRF-20261115-00101",
          balance: "9500.00"
        }));
      });
      return;
    }

    let filePath;
    if (reqPath === "/ui/transfer.html") {
      filePath = path.join(STATIC, "transfer.html");
    } else if (reqPath.startsWith("/ui/css/")) {
      filePath = path.join(STATIC, "css", path.basename(reqPath));
    } else if (reqPath.startsWith("/ui/js/")) {
      filePath = path.join(STATIC, "js", path.basename(reqPath));
    } else if (reqPath === "/ui/index.html") {
      filePath = path.join(STATIC, "index.html");
    } else {
      res.writeHead(404, { "Content-Type": "text/plain" });
      res.end("Not Found");
      return;
    }

    if (!fs.existsSync(filePath)) {
      res.writeHead(404, { "Content-Type": "text/plain" });
      res.end("Not Found");
      return;
    }

    const ext = path.extname(filePath);
    const contentType =
      ext === ".html" ? "text/html; charset=utf-8" :
      ext === ".css" ? "text/css; charset=utf-8" :
      ext === ".js" ? "application/javascript; charset=utf-8" : "application/octet-stream";

    res.writeHead(200, { "Content-Type": contentType });
    fs.createReadStream(filePath).pipe(res);
  });
}

(async () => {
  const server = createTestServer();
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const port = server.address().port;
  const baseUrl = `http://127.0.0.1:${port}`;

  const launchOpts = { headless: true };
  if (executablePath) {
    launchOpts.executablePath = executablePath;
  }

  const browser = await chromium.launch(launchOpts);
  console.log(`Launched browser: ${browser.version()} (${executablePath || "bundled"})`);

  try {
    // ----------------------------------------------------
    // 1. Narrow mobile viewport (360px x 800px)
    // ----------------------------------------------------
    const context = await browser.newContext({
      viewport: { width: 360, height: 800 }
    });

    // Provide authenticated Customer session before scripts run
    await context.addInitScript(() => {
      sessionStorage.setItem("bms_token", "test-token-cust");
      sessionStorage.setItem("bms_role", "Customer");
      sessionStorage.setItem("bms_username", "asharao");
      sessionStorage.setItem("bms_must_change", "false");
    });

    const page = await context.newPage();
    page.on("pageerror", (err) => console.error("Page error:", err));

    await page.goto(`${baseUrl}/ui/transfer.html`, { waitUntil: "domcontentloaded" });

    // Wait for accounts to load (options attached to DOM)
    await page.locator("#fromAccountSelect option:nth-child(2)").waitFor({ state: "attached", timeout: 5000 });

    // Check horizontal overflow at 360px
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    assert.ok(
      scrollWidth <= 360,
      `Page must not overflow horizontally at 360px viewport (actual scrollWidth: ${scrollWidth}px)`
    );

    // Verify key input elements have usable widths
    const inputWidth = await page.$eval("#toAccountInput", (el) => el.getBoundingClientRect().width);
    assert.ok(
      inputWidth >= 280,
      `Recipient input must have usable width on 360px screen (got ${inputWidth}px)`
    );

    const selectWidth = await page.$eval("#fromAccountSelect", (el) => el.getBoundingClientRect().width);
    assert.ok(
      selectWidth >= 280,
      `From account select must have usable width on 360px screen (got ${selectWidth}px)`
    );

    // Verify source account selection & live balance
    await page.selectOption("#fromAccountSelect", "1000000001");
    const isBalanceVisible = await page.$eval("#balanceDisplay", (el) => !el.hidden);
    assert.strictEqual(isBalanceVisible, true, "Balance card should be visible after selecting source account");

    // Fill transfer details
    await page.fill("#toAccountInput", "1000000003");

    // Verify invalid decimal precision (500.999) is rejected and does not advance
    await page.fill("#amountInput", "500.999");
    await page.click("#btnReview");
    const isErrorVisible = await page.$eval("#amountError", (el) => !el.hidden && el.textContent.includes("two decimal places"));
    assert.strictEqual(isErrorVisible, true, "Amount with >2 decimal places must show validation error");
    const didNotAdvance = await page.$eval("#stepReview", (el) => el.hidden);
    assert.strictEqual(didNotAdvance, true, "Form must not advance to review with invalid precision");

    // Fill valid amount
    await page.fill("#amountInput", "500.00");

    // Click Review button
    await page.click("#btnReview");

    // Verify Step 2 is shown and Step 1 is hidden
    const isReviewVisible = await page.$eval("#stepReview", (el) => !el.hidden);
    const isStep1Hidden = await page.$eval("#stepDetails", (el) => el.hidden);
    assert.strictEqual(isReviewVisible, true, "Review section must be visible in step 2");
    assert.strictEqual(isStep1Hidden, true, "Step 1 details must be hidden in step 2");

    // Check horizontal scroll width at Step 2
    const reviewScrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    assert.ok(
      reviewScrollWidth <= 360,
      `Review step must not overflow horizontally at 360px (actual: ${reviewScrollWidth}px)`
    );

    // Verify review summary values
    const reviewTo = await page.$eval("#reviewToAccount", (el) => el.textContent.trim());
    assert.strictEqual(reviewTo, "1000000003", "Review step should show recipient account");

    // Click Confirm & send transfer - verify exactly one request is sent
    const countBeforeSuccess = serverTransferCount;
    await page.click("#btnConfirmSend");

    // Verify Step 3 Success receipt
    await page.waitForSelector("#stepResult:not([hidden])");
    assert.strictEqual(
      serverTransferCount - countBeforeSuccess,
      1,
      "Exactly one transfer API call must be made on confirmation click (success case)"
    );

    const isSuccessVisible = await page.$eval("#successContent", (el) => !el.hidden);
    assert.strictEqual(isSuccessVisible, true, "Success content should be displayed");

    const receiptRef = await page.$eval("#receiptReference", (el) => el.textContent.trim());
    assert.strictEqual(receiptRef, "TRF-20261115-00101", "Receipt reference must match API response");

    const resultScrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    assert.ok(
      resultScrollWidth <= 360,
      `Receipt step must not overflow horizontally at 360px (actual: ${resultScrollWidth}px)`
    );

    // ----------------------------------------------------
    // Test Failure Handling in Browser with single request assertion
    // ----------------------------------------------------
    await page.click("#btnNewTransfer");
    await page.waitForSelector("#stepDetails:not([hidden])");

    // Re-fill form with non-existent destination account
    await page.selectOption("#fromAccountSelect", "1000000001");
    await page.fill("#toAccountInput", "9999999999");
    await page.fill("#amountInput", "250.00");
    await page.click("#btnReview");
    await page.waitForSelector("#stepReview:not([hidden])");

    const countBeforeFail = serverTransferCount;
    await page.click("#btnConfirmSend");

    await page.waitForSelector("#failureContent:not([hidden])");
    assert.strictEqual(
      serverTransferCount - countBeforeFail,
      1,
      "Exactly one transfer API call must be made on confirmation click (failure case)"
    );

    const failMsg = await page.$eval("#failureMessage", (el) => el.textContent.trim());
    assert.ok(
      failMsg.includes("recipient account was not found"),
      `Expected not-found error message, got: ${failMsg}`
    );

    // Verify back and correct details button restores Step 1
    await page.click("#btnFailureBack");
    await page.waitForSelector("#stepDetails:not([hidden])");

    console.log("✓ 360px mobile viewport verification (success, failure, single click) passed cleanly!");
    await context.close();

    // ----------------------------------------------------
    // 2. Desktop viewport (1024px x 768px)
    // ----------------------------------------------------
    const desktopContext = await browser.newContext({
      viewport: { width: 1024, height: 768 }
    });

    await desktopContext.addInitScript(() => {
      sessionStorage.setItem("bms_token", "test-token-cust");
      sessionStorage.setItem("bms_role", "Customer");
      sessionStorage.setItem("bms_username", "asharao");
      sessionStorage.setItem("bms_must_change", "false");
    });

    const desktopPage = await desktopContext.newPage();
    await desktopPage.goto(`${baseUrl}/ui/transfer.html`, { waitUntil: "domcontentloaded" });
    await desktopPage.locator("#fromAccountSelect option:nth-child(2)").waitFor({ state: "attached", timeout: 5000 });

    const navTitle = await desktopPage.$eval("#site-header h1", (el) => el.textContent);
    assert.ok(navTitle.includes("Transfer money"), "Desktop header must render title");

    console.log("✓ Desktop viewport verification passed cleanly!");
    await desktopContext.close();

  } finally {
    await browser.close();
    server.close();
  }
})().catch((err) => {
  console.error("transfer_browser_check failed:", err);
  process.exit(1);
});
