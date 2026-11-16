/* Genuine 360px mobile viewport verification for Firefox using Playwright's Gecko engine.
 * Authenticates as test Customer 1, executes canonical transfer journey,
 * measures actual browser DOM geometry without hardcoding, CSS injection, or iframes,
 * and asserts that the viewport is genuinely 360px with zero horizontal overflow.
 */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

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
const { firefox } = playwright;

const BASE_URL = process.env.BMS_BASE_URL || "http://127.0.0.1:8765";
const SHOT_DIR = process.env.BMS_SHOT_DIR || path.resolve(__dirname, "../../docs/test-plan/screenshots");
const OUT_FILE = process.env.BMS_FF_MOBILE_OUT || path.resolve(__dirname, "../../docs/test-plan/firefox_mobile_results.json");

fs.mkdirSync(SHOT_DIR, { recursive: true });

async function measureGeometry(page) {
  return await page.evaluate(() => {
    const cardEl = document.querySelector(".card:not([hidden])") || document.querySelector("#stepDetails");
    const indEl = document.querySelector(".steps-indicator");
    const dividers = Array.from(document.querySelectorAll(".step-divider")).map((el) => {
      const r = el.getBoundingClientRect();
      return parseFloat(r.width.toFixed(2));
    });
    const cardRect = cardEl ? cardEl.getBoundingClientRect() : { left: 0, right: 0, width: 0 };
    const indRect = indEl ? indEl.getBoundingClientRect() : { left: 0, right: 0, width: 0 };
    return {
      innerWidth: window.innerWidth,
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
      card: {
        left: parseFloat(cardRect.left.toFixed(2)),
        right: parseFloat(cardRect.right.toFixed(2)),
        width: parseFloat(cardRect.width.toFixed(2)),
      },
      stepsIndicator: {
        left: parseFloat(indRect.left.toFixed(2)),
        right: parseFloat(indRect.right.toFixed(2)),
        width: parseFloat(indRect.width.toFixed(2)),
      },
      stepDividers: dividers,
    };
  });
}

async function runFirefoxMobile() {
  console.log("Starting Firefox at genuine mobile_360 (360x800) via Playwright Gecko engine...");
  const browser = await firefox.launch({ headless: true });
  console.log(`Firefox engine version: ${browser.version()}`);

  const context = await browser.newContext({
    viewport: { width: 360, height: 800 },
  });
  const page = await context.newPage();

  // 1. Authenticated customer login journey
  await page.goto(`${BASE_URL}/ui/index.html`);
  await page.waitForSelector("#username");
  await page.fill("#username", "1");
  await page.fill("#password", "Passw0rd!");
  await page.click("button[type='submit']");
  await page.waitForURL("**/ui/customer.html");

  // 2. Navigate to canonical Transfer Money interface
  await page.click("nav a[href='/ui/transfer.html']");
  await page.waitForURL("**/ui/transfer.html");

  // Wait for accounts dropdown to load and select active account 1000000001
  await page.waitForFunction(() => {
    const sel = document.getElementById("fromAccountSelect");
    return sel && sel.options.length > 1;
  });
  await page.selectOption("#fromAccountSelect", "1000000001");

  // Verify balance displayed
  await page.waitForSelector("#accountBalanceDisplay");
  const balanceText = await page.$eval("#accountBalanceDisplay", (el) => el.textContent);
  assert.ok(balanceText.includes("10,000") || balanceText.includes("Rs") || balanceText.includes("₹"), "Balance display must show formatted balance");

  // Fill transfer details
  await page.fill("#toAccountInput", "1000000003");
  await page.fill("#amountInput", "500.00");

  // Stage 1: Details measurement
  const detailsGeo = await measureGeometry(page);
  // Genuine viewport assertions
  assert.strictEqual(detailsGeo.innerWidth, 360, `Firefox mobile innerWidth must be genuinely 360, got ${detailsGeo.innerWidth}`);
  assert.strictEqual(detailsGeo.clientWidth, 360, `Firefox mobile clientWidth must be genuinely 360, got ${detailsGeo.clientWidth}`);
  assert.ok(detailsGeo.scrollWidth <= detailsGeo.clientWidth, `scrollWidth (${detailsGeo.scrollWidth}) must not exceed clientWidth (${detailsGeo.clientWidth})`);

  const detailsShot = path.join(SHOT_DIR, "firefox_mobile_360_details.png");
  const overviewShot = path.join(SHOT_DIR, "firefox_mobile_360.png");
  await page.screenshot({ path: detailsShot, fullPage: false });
  await page.screenshot({ path: overviewShot, fullPage: false });

  // Stage 2: Review step
  await page.click("#btnReview");
  await page.waitForSelector("#stepReview:not([hidden])");
  const reviewGeo = await measureGeometry(page);
  assert.strictEqual(reviewGeo.innerWidth, 360, "Review innerWidth must be 360");
  assert.ok(reviewGeo.scrollWidth <= reviewGeo.clientWidth, "Review scrollWidth must not exceed clientWidth");

  const reviewShot = path.join(SHOT_DIR, "firefox_mobile_360_review.png");
  await page.screenshot({ path: reviewShot, fullPage: false });

  // Stage 3: Confirm and execute real transfer
  await page.click("#btnConfirmSend");
  await page.waitForSelector("#successContent:not([hidden])");

  // Verify receipt data
  const refText = await page.$eval("#receiptReference", (el) => el.textContent);
  assert.ok(refText.startsWith("TRF-"), "Receipt reference should begin with TRF-");
  const amtText = await page.$eval("#receiptAmount", (el) => el.textContent);
  assert.ok(amtText.includes("500.00"), "Receipt must confirm 500.00 transfer");

  const receiptGeo = await measureGeometry(page);
  assert.strictEqual(receiptGeo.innerWidth, 360, "Receipt innerWidth must be 360");
  assert.ok(receiptGeo.scrollWidth <= receiptGeo.clientWidth, "Receipt scrollWidth must not exceed clientWidth");

  const receiptShot = path.join(SHOT_DIR, "firefox_mobile_360_receipt.png");
  await page.screenshot({ path: receiptShot, fullPage: false });

  await browser.close();
  console.log("✓ Completed Firefox mobile_360 cleanly with genuine 360px viewport.");

  const results = {
    details: detailsGeo,
    review: reviewGeo,
    receipt: receiptGeo,
  };

  fs.writeFileSync(OUT_FILE, JSON.stringify(results, null, 2), "utf8");
}

runFirefoxMobile().catch((err) => {
  console.error("Firefox mobile verification error:", err);
  process.exit(1);
});
