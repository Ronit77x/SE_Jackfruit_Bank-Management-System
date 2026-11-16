/* Rendered browser regression test for Teller Accounts UI narrow screen responsiveness (US-15 / BMS-NF-006). */
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

// Static HTTP server for UI assets
function createStaticServer() {
  return http.createServer((req, res) => {
    const reqPath = req.url.split("?")[0];
    let filePath;
    if (reqPath === "/ui/teller-accounts.html") {
      filePath = path.join(STATIC, "teller-accounts.html");
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
  let server;
  let baseUrl = process.env.BMS_UI_TEST_URL;

  if (!baseUrl) {
    server = createStaticServer();
    await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
    const port = server.address().port;
    baseUrl = `http://127.0.0.1:${port}`;
  }

  const launchOpts = { headless: true };
  if (executablePath) {
    launchOpts.executablePath = executablePath;
  }

  const browser = await chromium.launch(launchOpts);
  console.log(`Launched browser: ${browser.version()} (${executablePath || "bundled"})`);

  try {
    // 1. Render at 360px viewport
    const context = await browser.newContext({
      viewport: { width: 360, height: 800 },
    });

    // Provide authenticated Teller session so requireRole succeeds without redirect
    await context.addInitScript(() => {
      sessionStorage.setItem("bms_token", "test-bearer-token");
      sessionStorage.setItem("bms_role", "Teller");
      sessionStorage.setItem("bms_must_change", "false");
      sessionStorage.setItem("bms_username", "testteller");
    });

    const page = await context.newPage();
    const pageErrors = [];
    page.on("pageerror", (err) => pageErrors.push(err.message));

    await page.goto(`${baseUrl}/ui/teller-accounts.html`, { waitUntil: "domcontentloaded" });
    await page.locator("#search-query").waitFor({ state: "visible", timeout: 5000 });

    // Measure rendered geometries
    const metrics = await page.evaluate(() => {
      const input = document.getElementById("search-query");
      const submit = document.getElementById("search-submit");
      const clear = document.getElementById("search-clear");
      const inputRect = input.getBoundingClientRect();
      const submitRect = submit.getBoundingClientRect();
      const clearRect = clear.getBoundingClientRect();

      return {
        viewportWidth: window.innerWidth,
        docScrollWidth: document.documentElement.scrollWidth,
        docClientWidth: document.documentElement.clientWidth,
        input: {
          width: inputRect.width,
          height: inputRect.height,
          top: inputRect.top,
          left: inputRect.left,
          bottom: inputRect.bottom,
        },
        submit: {
          width: submitRect.width,
          height: submitRect.height,
          top: submitRect.top,
          left: submitRect.left,
          bottom: submitRect.bottom,
        },
        clear: {
          width: clearRect.width,
          height: clearRect.height,
          top: clearRect.top,
          left: clearRect.left,
          bottom: clearRect.bottom,
        },
      };
    });

    console.log("360px Rendered Metrics:", JSON.stringify(metrics, null, 2));

    // Assertion 1: Input has usable width (>= 250px, actual is 310px)
    assert.ok(
      metrics.input.width >= 250,
      `Search input width must be at least 250px, got ${metrics.input.width}px`
    );

    // Assertion 2: Search and Clear controls remain visible and usable
    assert.ok(await page.locator("#search-submit").isVisible(), "Search submit button must be visible");
    assert.ok(await page.locator("#search-clear").isVisible(), "Search clear button must be visible");
    assert.ok(metrics.submit.width >= 250, `Search submit button width must be at least 250px, got ${metrics.submit.width}px`);
    assert.ok(metrics.clear.width >= 250, `Search clear button width must be at least 250px, got ${metrics.clear.width}px`);

    // Verify controls are stacked vertically on narrow screen
    assert.ok(
      metrics.submit.top >= metrics.input.bottom - 1,
      `Submit button top (${metrics.submit.top}) should be below input bottom (${metrics.input.bottom})`
    );
    assert.ok(
      metrics.clear.top >= metrics.submit.bottom - 1,
      `Clear button top (${metrics.clear.top}) should be below submit bottom (${metrics.submit.bottom})`
    );

    // Assertion 3: Page does not have horizontal overflow
    assert.ok(
      metrics.docScrollWidth <= metrics.docClientWidth,
      `Page must not have horizontal overflow: scrollWidth (${metrics.docScrollWidth}px) > clientWidth (${metrics.docClientWidth}px)`
    );
    assert.strictEqual(metrics.docClientWidth, 360, "Client width must match 360px viewport");

    // Assertion 4: Interactive verification on narrow screen
    await page.locator("#search-query").fill("Sharma");
    assert.strictEqual(await page.locator("#search-query").inputValue(), "Sharma");

    await page.locator("#search-clear").click();
    assert.strictEqual(await page.locator("#search-query").inputValue(), "");

    await page.locator("#search-submit").click();
    await page.locator("#search-message").filter({ hasText: "Enter a name, phone number, or account number." }).waitFor();

    // Assertion 5: Verify desktop (1280px) layout is preserved
    await page.setViewportSize({ width: 1280, height: 900 });
    const desktopMetrics = await page.evaluate(() => {
      const input = document.getElementById("search-query");
      const submit = document.getElementById("search-submit");
      const clear = document.getElementById("search-clear");
      const inputRect = input.getBoundingClientRect();
      const submitRect = submit.getBoundingClientRect();
      const clearRect = clear.getBoundingClientRect();
      return {
        inputWidth: inputRect.width,
        submitTop: submitRect.top,
        clearTop: clearRect.top,
        inputTop: inputRect.top,
      };
    });

    console.log("1280px Desktop Metrics:", JSON.stringify(desktopMetrics, null, 2));
    // On desktop, controls should be side-by-side (same line / row)
    assert.ok(
      Math.abs(desktopMetrics.submitTop - desktopMetrics.inputTop) < 15,
      "On desktop, search submit button should align with input horizontally"
    );
    assert.ok(
      Math.abs(desktopMetrics.clearTop - desktopMetrics.inputTop) < 15,
      "On desktop, search clear button should align with input horizontally"
    );

    assert.strictEqual(pageErrors.length, 0, `Page errors encountered: ${pageErrors.join("; ")}`);
    console.log("Teller Accounts rendered-browser regression checks PASSED.");

    await context.close();
  } finally {
    await browser.close();
    if (server) {
      await new Promise((resolve) => server.close(resolve));
    }
  }
})();
