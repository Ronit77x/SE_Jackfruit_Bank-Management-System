/* Cross-browser test runner for Chrome and Edge using Playwright.
 * Authenticates as test Customer 1 (Asha Rao), performs canonical transfer journey,
 * captures 1280px desktop and 360px mobile screenshots, and extracts layout geometry.
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
const { chromium } = playwright;

const BASE_URL = process.env.BMS_BASE_URL || "http://127.0.0.1:8765";
const SHOT_DIR = process.env.BMS_SHOT_DIR || path.resolve(__dirname, "../../docs/test-plan/screenshots");
const OUT_FILE = process.env.BMS_OUT_JSON || path.resolve(__dirname, "../../docs/test-plan/playwright_results.json");

fs.mkdirSync(SHOT_DIR, { recursive: true });

const BROWSERS = [
  {
    name: "chrome",
    executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  },
  {
    name: "edge",
    executablePath: "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  },
];

const VIEWPORTS = [
  { key: "desktop_1280", width: 1280, height: 800 },
  { key: "mobile_360", width: 360, height: 800 },
];

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

async function runBrowser(browserConfig, vpConfig) {
  console.log(`Starting ${browserConfig.name} at ${vpConfig.key} (${vpConfig.width}x${vpConfig.height})...`);
  const browser = await chromium.launch({
    executablePath: browserConfig.executablePath,
    headless: true,
  });

  const context = await browser.newContext({
    viewport: { width: vpConfig.width, height: vpConfig.height },
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

  // Wait for accounts dropdown to be loaded with options
  await page.waitForFunction(() => {
    const sel = document.getElementById("fromAccountSelect");
    return sel && sel.options.length > 1;
  });

  // Select active source account 1000000001
  await page.selectOption("#fromAccountSelect", "1000000001");

  // Verify balance displayed
  await page.waitForSelector("#accountBalanceDisplay");
  const balanceText = await page.$eval("#accountBalanceDisplay", (el) => el.textContent);
  assert.ok(balanceText.includes("10,000") || balanceText.includes("Rs") || balanceText.includes("₹"), "Balance display must show formatted balance");

  // Fill transfer details
  await page.fill("#toAccountInput", "1000000003");
  await page.fill("#amountInput", "500.00");

  // Stage 1: Details measurement & screenshots
  const detailsGeo = await measureGeometry(page);
  assert.strictEqual(detailsGeo.innerWidth, vpConfig.width, `innerWidth must match requested width ${vpConfig.width}`);
  assert.ok(detailsGeo.scrollWidth <= detailsGeo.clientWidth, `Details scrollWidth (${detailsGeo.scrollWidth}) must not exceed clientWidth (${detailsGeo.clientWidth})`);
  const detailsShot = path.join(SHOT_DIR, `${browserConfig.name}_${vpConfig.key}_details.png`);
  const overviewShot = path.join(SHOT_DIR, `${browserConfig.name}_${vpConfig.key}.png`);
  await page.screenshot({ path: detailsShot, fullPage: false });
  await page.screenshot({ path: overviewShot, fullPage: false });

  // Stage 2: Review step
  await page.click("#btnReview");
  await page.waitForSelector("#stepReview:not([hidden])");
  const reviewGeo = await measureGeometry(page);
  assert.ok(reviewGeo.scrollWidth <= reviewGeo.clientWidth, `Review scrollWidth (${reviewGeo.scrollWidth}) must not exceed clientWidth (${reviewGeo.clientWidth})`);
  const reviewShot = path.join(SHOT_DIR, `${browserConfig.name}_${vpConfig.key}_review.png`);
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
  assert.ok(receiptGeo.scrollWidth <= receiptGeo.clientWidth, `Receipt scrollWidth (${receiptGeo.scrollWidth}) must not exceed clientWidth (${receiptGeo.clientWidth})`);
  const receiptShot = path.join(SHOT_DIR, `${browserConfig.name}_${vpConfig.key}_receipt.png`);
  await page.screenshot({ path: receiptShot, fullPage: false });

  await browser.close();
  console.log(`✓ Completed ${browserConfig.name} at ${vpConfig.key} cleanly.`);

  return {
    details: detailsGeo,
    review: reviewGeo,
    receipt: receiptGeo,
  };
}

async function main() {
  const results = {};

  for (const b of BROWSERS) {
    results[b.name] = {};
    for (const vp of VIEWPORTS) {
      results[b.name][vp.key] = await runBrowser(b, vp);
    }
  }

  fs.writeFileSync(OUT_FILE, JSON.stringify(results, null, 2), "utf8");
  console.log(`Playwright browser results written to ${OUT_FILE}`);
}

main().catch((err) => {
  console.error("Playwright verification error:", err);
  process.exit(1);
});
