# Browser Compatibility & Responsive UI Test Report: TC-UX-02

- **Test Case ID:** `TC-UX-02`
- **User Story:** `[US-15] Browser compatibility & responsive UI` (GitHub Issue #13)
- **Requirement:** `BMS-NF-006` — Browser compatibility and 360 px UI
- **Component:** `DS-UI` (Customer Web Interface)
- **Assigned Member:** Member 2 (Vijay Kumar)
- **Sprint:** Sprint 2
- **Story Points:** 2

---

## 1. Test Objectives & Acceptance Criteria

Verify that the Bank Management System customer web application satisfies `BMS-NF-006`:
1. **Cross-Browser Compatibility:** The UI must render and operate properly across the **latest two versions** of:
   - Google Chrome (Chromium)
   - Microsoft Edge (Chromium)
   - Mozilla Firefox (Gecko)
2. **Responsive Mobile Benchmark:** The UI must remain usable, legible, and functional at a **360 px viewport width** without unintended horizontal scrolling or broken controls.
3. **Core Workflows Evaluated on Canonical UI (`/ui/transfer.html`):**
   - User authentication and session integration (`POST /auth/login` as test Customer 1 Asha Rao).
   - Dynamic account retrieval and status filtering (`GET /accounts/me` rendering eligible Active accounts and disabling Frozen accounts).
   - 3-stage fund transfer interface flow:
     - **Stage 1 (Details):** Source account selection, recipient input (`1000000003`), amount input (`500.00`) with real-time validations.
     - **Stage 2 (Review):** Transfer review summary card with masked source, destination, amount, and free fee details.
     - **Stage 3 (Receipt):** Immediate confirmation with transaction reference number (`TRF-...`) and updated source balance (Rs 9,500.00).
   - Form controls, inputs, and real-time validations
   - Page navigation, layout rendering, and alerts
   - Receipt printing (`window.print()`)

---

## 2. Test Environment & System Specifications

- **Operating System:** Windows 10/11 Home/Pro (Build 26100, x86_64 / win32)
- **Test Server:** Live FastAPI application running Uvicorn (`http://127.0.0.1:8765`) backed by SQLite test database
- **Locally Installed & Verified Browser Binaries:**
  - **Google Chrome:** Version `157.0.8103.51` (Official Build, 64-bit)
  - **Microsoft Edge:** Version `157.0.4341.60` (Official Build, 64-bit)
  - **Mozilla Firefox Desktop:** Version `159.0` (Official Build, 64-bit) via Selenium WebDriver & GeckoDriver
  - **Mozilla Firefox Mobile (Gecko Engine):** Version `153.0` via Playwright Firefox layout viewport emulation
- **Viewports Evaluated:**
  - **Mobile Benchmark:** `360 px × 800 px` (BMS-NF-006 target)
  - **Desktop Standard:** `1280 px × 800 px`
- **Important Windows OS Limitation Note:**
  - Under the Windows OS Win32 window manager, native top-level windows for Mozilla Firefox enforce a minimum window tracking width of 500 px (`ptMinTrackSize.x = 500`). When Selenium GeckoDriver issues `driver.set_window_size(360, 800)` to the native desktop binary, the OS window manager clamps `window.innerWidth` and `clientWidth` to `500 px`.
  - Rather than artificially masking this limitation with CSS width injection or iframe wrappers, our test harness reports this native OS behavior transparently (`system_firefox_selenium_windows_limitation` in `browser_verification_results.json`) and verifies the genuine 360 px mobile Gecko layout engine directly via Playwright Gecko's viewport layout emulation, measuring authentic browser DOM properties.

---

## 3. Browser & Version Compatibility Matrix

Per course engineering standards, this matrix strictly distinguishes between **currently installed & executed versions** versus **uninstalled previous versions** ($n-1$). Previous versions are marked as pending external lab execution.

| Browser | Version | Engine | Status | Testing Method | Evidence / Artifacts |
| :--- | :---: | :---: | :---: | :--- | :--- |
| **Google Chrome** | `157.0.8103.51` | Blink / Chromium | **PASS** | Automated Playwright execution on canonical UI (`/ui/transfer.html`) | Full-journey screenshots `chrome_desktop_1280_*.png`, `chrome_mobile_360_*.png` (Details, Review, Receipt) |
| **Google Chrome** | `155.x` ($n-1$) | Blink / Chromium | **PENDING** | *Not installed locally on test machine* | Requires multi-version CI or cloud browser farm (e.g. BrowserStack) |
| **Microsoft Edge** | `157.0.4341.60` | Blink / Chromium | **PASS** | Automated Playwright execution on canonical UI (`/ui/transfer.html`) | Full-journey screenshots `edge_desktop_1280_*.png`, `edge_mobile_360_*.png` (Details, Review, Receipt) |
| **Microsoft Edge** | `155.x` ($n-1$) | Blink / Chromium | **PENDING** | *Not installed locally on test machine* | Requires multi-version CI or cloud browser farm (e.g. BrowserStack) |
| **Mozilla Firefox Desktop** | `159.0` | Gecko | **PASS** | Automated Selenium execution on canonical UI (`/ui/transfer.html`) | Full-journey screenshots `firefox_desktop_1280_*.png` (Details, Review, Receipt) |
| **Mozilla Firefox Mobile** | `153.0` | Gecko | **PASS** | Automated Playwright Gecko execution (genuine 360 px viewport) | Full-journey screenshots `firefox_mobile_360_*.png` (Details, Review, Receipt) |
| **Mozilla Firefox** | `146.x` ($n-1$) | Gecko | **PENDING** | *Not installed locally on test machine* | Requires multi-version CI or cloud browser farm (e.g. BrowserStack) |

---

## 4. Evidence Classification & Methodology Distinction

Testing evidence is explicitly structured into two complementary categories:

### Category A: Genuine End-to-End Browser Journey & Responsive Visual Compatibility
This evaluates real browser layout engines (Blink in Chrome/Edge, Gecko in Firefox) executing against the live backend server:

1. **Authentication:** The test browser logs in at `/ui/index.html` with test customer credentials (username `1`, password `Passw0rd!`).
2. **Navigation:** Follows the customer portal navigation to the canonical transfer page `/ui/transfer.html`.
3. **Data Retrieval:** Dynamically loads customer accounts (`GET /accounts/me`), verifying active accounts are selectable and frozen accounts are disabled.
4. **Validation & Review:** Enforces decimal precision (at most two decimal places) and transfers funds through the 3-stage wizard.
5. **Real Transaction Persistence:** Confirms receipt generation and balance update (Rs 10,000.00 $\to$ Rs 9,500.00).
6. **Geometry & Layout:** Directly measures `scrollWidth`, `clientWidth`, and container bounding rects across all viewports without hardcoding or CSS overrides.

#### 360 px Mobile Viewport Measurements:

| Layout Element / Metric | Chrome 157 Mobile | Edge 157 Mobile | Firefox Gecko Mobile | Acceptance Benchmark | Status |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Viewport Width (`innerWidth`)** | 360 px | 360 px | 360 px | 360 px target | **PASS** |
| **Client Width (`clientWidth`)** | 360 px | 360 px | 360 px | 360 px | **PASS** |
| **Rendered Content Width (`scrollWidth`)** | **360 px** | **360 px** | **360 px** | $\le 360$ px | **PASS** |
| **Horizontal Overflow** | **0 px** | **0 px** | **0 px** | **0 px (No horizontal scroll)** | **PASS** |
| **Card Width (`.card`)** | 340 px | 340 px | 340 px | Contained within 360 px | **PASS** |
| **Step Indicator Width (`.steps-indicator`)** | 340 px | 340 px | 340 px | Contained within card | **PASS** |
| **Step Divider Rendering** | Fluid [63.16, 63.17] px | Fluid [63.16, 63.17] px | Fluid [63.12, 63.12] px | No layout break | **PASS** |
| **Right-Edge Pixel Clipping ($x=359$)** | 0 clipped elements | 0 clipped elements | 0 clipped elements | 0 clipped pixels | **PASS** |

Complete layout geometry records for all stages are saved in `docs/test-plan/browser_verification_results.json`.

#### Firefox Windows OS Native Window Limitation Details:
- When executing Selenium WebDriver against the installed Windows system Firefox binary (`firefox.exe`) with `driver.set_window_size(360, 800)`, the underlying Windows Win32 window manager enforces a minimum window tracking size:
  - Measured `innerWidth`: 500 px
  - Measured `clientWidth`: 500 px
  - Measured `scrollWidth`: 500 px
- Our test suite transparently records this native platform constraint under `selenium_system_firefox_windows_limitation` in `browser_verification_results.json`.
- Genuine 360 px Gecko engine layout verification was performed using Playwright's Gecko engine, which operates layout viewport emulation at the engine level without native window manager clipping, confirming that Gecko natively renders the canonical responsive layout at 360 px with 0 px horizontal overflow (`scrollWidth === 360 px`).

### Category B: Automated Backend & Contract Regression Evidence (`pytest`)

Backend API contracts, database operations, session management, and business logic are tested and proven by automated test suites executed via FastAPI `TestClient`:

- **Browser & UI Contract Tests (`tests/test_accounts_browser_compatibility.py` — 11 passed):** Verifies canonical markup, `<meta name="viewport">`, number spinner normalization (`-moz-appearance: textfield`), responsive media queries (`@media (max-width: 480px)` and `@media (max-width: 380px)`), print stylesheets (`@media print`), accessible form attributes (`aria`, `inputmode`, `pattern`), client script safety, and HTTP endpoint serving.
- **Transfer UI & Account Services (`tests/test_accounts_transfer_ui.py` — 27 passed):** Verifies customer account retrieval (`GET /accounts/me`), exclusion of ineligible/frozen/closed accounts, session logout and token revocation, transfer validation rules, decimal precision rejection (`500.999`), and business rule enforcement independent of the frontend.
- **JavaScript Static & Unit Checks (`tests/ui/transfer_check.js` — passed):** Verifies raw amount validation, edge-case decimal rejection, and form validation logic.
- **Full Repository Suite (`pytest -q` — 448 passed, 1 warning):** 100% pass rate across the full platform test suite.

---

## 5. Rendered Browser Screenshot Evidence (Canonical Application Catalog)

The following screenshots document the live canonical application UI (`app/static/transfer.html`) captured from genuine browser sessions:

### Canonical Visual-State Screenshots (3 Stages × 2 Viewports × 3 Browsers)

| Browser | Viewport | Visual Stage | Artifact File | Dimensions | File Size | Rendered Visual Description |
| :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| **Google Chrome 157** | Desktop | 1. Details | `docs/test-plan/screenshots/chrome_desktop_1280_details.png` | 1280 × 800 | 53,790 B | Authenticated transfer page, active source account, balance Rs 10,000.00, recipient `1000000003`, amount `500.00` |
| **Google Chrome 157** | Desktop | 2. Review | `docs/test-plan/screenshots/chrome_desktop_1280_review.png` | 1280 × 800 | 36,079 B | Step 2 active, review summary card with source `1000000001`, recipient `1000000003`, amount Rs 500.00, free fee |
| **Google Chrome 157** | Desktop | 3. Receipt | `docs/test-plan/screenshots/chrome_desktop_1280_receipt.png` | 1280 × 800 | 34,939 B | Step 3 active, green checkmark, reference `TRF-...`, debited balance Rs 9,500.00, Print Receipt button |
| **Google Chrome 157** | Mobile | 1. Details | `docs/test-plan/screenshots/chrome_mobile_360_details.png` | 360 × 800 | 45,385 B | Single-column 360 px mobile layout, fluid inputs, step 1 active, 0 px horizontal overflow |
| **Google Chrome 157** | Mobile | 2. Review | `docs/test-plan/screenshots/chrome_mobile_360_review.png` | 360 × 800 | 29,904 B | Step 2 active, responsive review summary contained within 340 px card, stacked action buttons |
| **Google Chrome 157** | Mobile | 3. Receipt | `docs/test-plan/screenshots/chrome_mobile_360_receipt.png` | 360 × 800 | 29,196 B | Step 3 active, confirmation layout, Print Receipt and Make Another Transfer buttons, 0 px overflow |
| **Microsoft Edge 157** | Desktop | 1. Details | `docs/test-plan/screenshots/edge_desktop_1280_details.png` | 1280 × 800 | 53,714 B | Authenticated transfer page, active source account, balance Rs 10,000.00, recipient `1000000003`, amount `500.00` |
| **Microsoft Edge 157** | Desktop | 2. Review | `docs/test-plan/screenshots/edge_desktop_1280_review.png` | 1280 × 800 | 36,079 B | Step 2 active, review summary card with source `1000000001`, recipient `1000000003`, amount Rs 500.00, free fee |
| **Microsoft Edge 157** | Desktop | 3. Receipt | `docs/test-plan/screenshots/edge_desktop_1280_receipt.png` | 1280 × 800 | 34,772 B | Step 3 active, green checkmark, reference `TRF-...`, debited balance Rs 9,500.00, Print Receipt button |
| **Microsoft Edge 157** | Mobile | 1. Details | `docs/test-plan/screenshots/edge_mobile_360_details.png` | 360 × 800 | 45,286 B | Single-column 360 px mobile layout, fluid inputs, step 1 active, 0 px horizontal overflow |
| **Microsoft Edge 157** | Mobile | 2. Review | `docs/test-plan/screenshots/edge_mobile_360_review.png` | 360 × 800 | 29,904 B | Step 2 active, responsive review summary contained within 340 px card, stacked action buttons |
| **Microsoft Edge 157** | Mobile | 3. Receipt | `docs/test-plan/screenshots/edge_mobile_360_receipt.png` | 360 × 800 | 29,011 B | Step 3 active, confirmation layout, Print Receipt and Make Another Transfer buttons, 0 px overflow |
| **Mozilla Firefox 159** | Desktop | 1. Details | `docs/test-plan/screenshots/firefox_desktop_1280_details.png` | 1280 × 715 | 49,454 B | Authenticated transfer page, active source account, balance Rs 10,000.00, recipient `1000000003`, amount `500.00` |
| **Mozilla Firefox 159** | Desktop | 2. Review | `docs/test-plan/screenshots/firefox_desktop_1280_review.png` | 1280 × 715 | 35,297 B | Step 2 active, review summary card with source `1000000001`, recipient `1000000003`, amount Rs 500.00, free fee |
| **Mozilla Firefox 159** | Desktop | 3. Receipt | `docs/test-plan/screenshots/firefox_desktop_1280_receipt.png` | 1280 × 715 | 34,636 B | Step 3 active, green checkmark, reference `TRF-...`, debited balance Rs 9,500.00, Print Receipt button |
| **Mozilla Firefox (Gecko)** | Mobile | 1. Details | `docs/test-plan/screenshots/firefox_mobile_360_details.png` | 360 × 800 | 37,739 B | Single-column 360 px layout, Gecko normalized number input, 0 px horizontal overflow |
| **Mozilla Firefox (Gecko)** | Mobile | 2. Review | `docs/test-plan/screenshots/firefox_mobile_360_review.png` | 360 × 800 | 26,486 B | Step 2 active, review summary contained within 340 px card, 0 px horizontal overflow |
| **Mozilla Firefox (Gecko)** | Mobile | 3. Receipt | `docs/test-plan/screenshots/firefox_mobile_360_receipt.png` | 360 × 800 | 26,366 B | Step 3 active, confirmation layout, Print Receipt and Make Another Transfer buttons |

### Base Visual Screenshots (Maintained for Backward Compatibility)

| Screenshot File | Resolution | File Size | Description |
| :--- | :---: | :---: | :--- |
| `docs/test-plan/screenshots/chrome_desktop_1280.png` | 1280 × 800 | 53,790 B | Chrome 157 Desktop: Canonical transfer interface overview |
| `docs/test-plan/screenshots/chrome_mobile_360.png` | 360 × 800 | 45,385 B | Chrome 157 Mobile (360px): Verified zero horizontal overflow |
| `docs/test-plan/screenshots/edge_desktop_1280.png` | 1280 × 800 | 53,714 B | Edge 157 Desktop: Canonical transfer interface overview |
| `docs/test-plan/screenshots/edge_mobile_360.png` | 360 × 800 | 45,286 B | Edge 157 Mobile (360px): Fluid inputs and responsive step indicator |
| `docs/test-plan/screenshots/firefox_desktop_1280.png` | 1280 × 715 | 49,454 B | Firefox 159 Desktop: Gecko rendering with normalized spin buttons |
| `docs/test-plan/screenshots/firefox_mobile_360.png` | 360 × 800 | 37,739 B | Firefox Gecko Mobile (360px): Normalized amount input and touch targets |

---

## 6. Implementation Summary & Cross-Browser Hardening

1. **Canonical Application Integration:**
   - Evaluated the genuine customer application at `app/static/transfer.html` with modular CSS at `app/static/css/transfer.css` and JavaScript controller at `app/static/js/transfer.js`.
   - Verified that all authentication guards (`bms.requireRole(["Customer"])`), site headers (`bms.header()`), and navigation links integrate seamlessly with the shared application structure.
2. **Numeric Spin Button Normalization:**
   - Chrome/Edge (WebKit/Blink) spin buttons suppressed using `input[type="number"]::-webkit-outer-spin-button, input[type="number"]::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }`.
   - Firefox (Gecko) spin buttons suppressed using `input[type="number"] { -moz-appearance: textfield; appearance: textfield; }`.
3. **Responsive Breakpoints & Zero Overflow:**
   - Added media queries `@media (max-width: 480px)` and `@media (max-width: 380px)` to `app/static/css/transfer.css`.
   - Scaled step indicators, fluid dividers (`min-width: 4px; flex: 1 1 6px`), card padding, and button groups (`flex-direction: column-reverse`).
   - Verified that `scrollWidth === clientWidth === 360px` with 0 horizontal overflow across all browsers.
4. **Receipt Print Stylesheet:**
   - Clean `@media print` rules hide headers, step indicators, action buttons, alerts, and quick-pick buttons to produce an uncluttered customer receipt.
5. **Accessibility & Form Standards:**
   - Standard labels (`for="fromAccountSelect"`, `for="toAccountInput"`, `for="amountInput"`), numeric input mode (`inputmode="numeric"`), pattern enforcement (`pattern="[0-9]{10}"`), and ARIA alert roles (`role="alert"`).

---

## 7. Remaining Actions & Pull Request Targeting

1. **Prior Minor Versions ($n-1$):**
   - Verification for Chrome 155, Edge 155, and Firefox 146 remains pending access to an external device laboratory (BrowserStack or SauceLabs) or a dedicated multi-version CI pipeline.
2. **Pull Request Target:**
   - PR #61 targets `feature/US-14-fund-transfer-usability` (PR #60), preserving the canonical fund transfer implementation and integrating all latest review updates.
