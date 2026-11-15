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
3. **Core Workflows Evaluated:**
   - User login interface and session state rendering
   - Account viewing interface (masked account display and balance rendering)
   - 3-stage fund transfer interface flow:
     - **Stage 1 (Details):** Source account selection, recipient input, amount input with real-time validations.
     - **Stage 2 (Review):** Transfer review summary card with masked source, destination, amount, and fee details.
     - **Stage 3 (Receipt):** Immediate confirmation with transaction reference number and updated source balance.
   - Form controls, inputs, and real-time validations
   - Page navigation, layout rendering, and alerts
   - Receipt printing (`window.print()`)

---

## 2. Test Environment & System Specifications

- **Operating System:** Windows 10/11 Home/Pro (Build 26100, x86_64 / win32)
- **Locally Installed & Verified Browser Binaries:**
  - **Google Chrome:** Version `157.0.8103.51` (Official Build, 64-bit)
  - **Microsoft Edge:** Version `157.0.4341.57` (Official Build, 64-bit)
  - **Mozilla Firefox:** Version `159.0` (Official Build, 64-bit)
- **Viewports Evaluated:**
  - **Mobile Benchmark:** `360 px × 800 px` (BMS-NF-006 target)
  - **Mobile Common:** `375 px × 667 px`, `412 px × 915 px`
  - **Tablet:** `768 px × 1024 px`
  - **Desktop Standard:** `1280 px × 800 px`

---

## 3. Browser & Version Compatibility Matrix

Per reviewer feedback, this matrix strictly distinguishes between **currently installed & executed versions** versus **uninstalled previous versions** ($n-1$). Previous versions are not marked as tested without direct evidence.

| Browser | Version | Engine | Status | Testing Method | Evidence / Artifacts |
| :--- | :---: | :---: | :---: | :--- | :--- |
| **Google Chrome** | `157.0.8103.51` | Blink / Chromium | **PASS** | Automated Selenium & CDP headless execution (`--headless=new`) | Visual-state screenshots `chrome_desktop_1280_*.png`, `chrome_mobile_360_*.png` (Details, Review, Receipt) |
| **Google Chrome** | `155.x` ($n-1$) | Blink / Chromium | **PENDING** | *Not installed locally on test machine* | Requires multi-version CI or cloud browser farm (e.g. BrowserStack) |
| **Microsoft Edge** | `157.0.4341.57` | Blink / Chromium | **PASS** | Automated Selenium & CDP headless execution (`--headless=new`) | Visual-state screenshots `edge_desktop_1280_*.png`, `edge_mobile_360_*.png` (Details, Review, Receipt) |
| **Microsoft Edge** | `155.x` ($n-1$) | Blink / Chromium | **PENDING** | *Not installed locally on test machine* | Requires multi-version CI or cloud browser farm (e.g. BrowserStack) |
| **Mozilla Firefox** | `159.0` | Gecko | **PASS** | Automated Selenium & native headless binary execution (`--headless`) | Visual-state screenshots `firefox_desktop_1280_*.png`, `firefox_mobile_360_*.png` (Details, Review, Receipt) |
| **Mozilla Firefox** | `146.x` ($n-1$) | Gecko | **PENDING** | *Not installed locally on test machine* | Requires multi-version CI or cloud browser farm (e.g. BrowserStack) |

---

## 4. Evidence Classification & Methodology Distinction

To ensure strict engineering integrity, testing evidence is explicitly separated into two distinct categories:

### Category A: Responsive Visual Compatibility Evidence (Client-Side Rendering)
This evaluates real browser layout engines (Blink in Chrome/Edge, Gecko in Firefox) rendering `transfer.html` across viewports.

> [!IMPORTANT]
> **Nature of Visual Screenshots:**
> The 18 stage screenshots demonstrate **client-side visual-state rendering and responsive layout geometry**. They were captured by initializing client-side UI states in headless browser sessions to verify how each browser renders form controls, step indicators, masked accounts, review summaries, and receipt layouts at 360 px and 1280 px.
>
> **Scope Limitations:**
> - These visual-state screenshots do **not** establish successful authentication through `POST /auth/login`.
> - They do **not** establish dynamic account retrieval from a live server via `GET /accounts/me`.
> - They do **not** establish a persisted transfer through `POST /transactions/transfer`.
> - They do **not** prove database balance changes or database transaction record creation.
>
> Backend transactional workflows are verified independently in Category B via automated test suites.

#### Before vs. After 360 px Mobile Viewport Measurements:

| Layout Element / Metric | Prior Commit (`897f9ed`) | After Responsive Fix | Status |
| :--- | :---: | :---: | :--- |
| **Viewport Width (`innerWidth`)** | 360 px | 360 px | Benchmark Target |
| **Client Width (`clientWidth`)** | 360 px | 360 px | Full viewport fill |
| **Rendered Content Width (`scrollWidth`)** | ~366 px to 372 px (Overflow) | **360 px** | **Zero horizontal overflow** |
| **Horizontal Overflow** | +6 px to +12 px (Horizontal scrollbar) | **0 px** | **PASS** |
| **Card Container Width (`.card`)** | 340 px (`width: calc(100% - 20px)`) | 340 px (`left: 10px`, `right: 350px`) | Perfectly centered with 10 px gutters |
| **Step Indicator Width (`.steps-indicator`)** | ~366 px (Overflowed card bounds) | 340 px (`left: 10px`, `right: 350px`) | Contained inside card |
| **Step Divider Widths (`.step-divider`)** | Fixed 14 px / 32 px | Fluid `flex: 1 1 6px` | Adapts fluidly |
| **Demo Login Controls (`.demo-controls`)** | Inline horizontal flex wrap (pushed right) | Vertical block stack (100% width) | Zero overflow |
| **Right-Edge Pixel Clipping ($x=359$)** | Clipped blue button/divider pixels | **0 clipped controls** | **PASS** |

#### Intrinsic Overflow Audit:
When `overflow-x: clip` and `overflow-x: hidden` are temporarily removed (`style.overflowX = 'visible'`) in Chrome, Edge, and Firefox, `document.documentElement.scrollWidth` and `document.body.scrollWidth` remain exactly **360 px** (`difference = 0 px`). This confirms the responsive CSS rules solve the underlying layout geometry and do not merely hide an uncorrected overflow defect.

### Category B: Backend Functional & Contract Evidence (`pytest`)
Backend API contracts, database operations, session management, and business logic are tested and proven by automated test suites executed via FastAPI `TestClient`:

- **Browser & UI Contract Tests (`tests/test_accounts_browser_compatibility.py` — 8 passed):** Verifies `<meta name="viewport">`, number spinner normalization (`-moz-appearance: textfield`), responsive media queries (`@media (max-width: 480px)` and `@media (max-width: 380px)`), print stylesheets (`@media print`), accessible form attributes (`aria`, `inputmode`), and exclusion of obsolete APIs.
- **Transfer UI & Account Services (`tests/test_accounts_transfer_ui.py` — 25 passed):** Verifies customer account retrieval (`GET /accounts/me`), exclusion of ineligible/frozen/closed accounts, session logout and token revocation, transfer validation rules, and business rule enforcement independent of the frontend.
- **Authentication & Security (`tests/test_auth.py` — 12 passed):** Verifies login token generation, password verification, 3-attempt account lockout, audit log emission, and administrative unlocking.
- **Full Repository Suite (`pytest -q` — 108 passed, 1 warning):** 100% pass rate across all platform unit, integration, and security tests.

---

## 5. Rendered Browser Screenshot Evidence (Visual-State Catalog)

The following screenshots document the rendered visual appearance across installed browser binaries:

### Client Visual-State Screenshots (3 Stages × 2 Viewports × 3 Browsers)

| Browser | Viewport | Visual Stage | Artifact File | Dimensions | File Size | Rendered Visual Description |
| :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| **Google Chrome 157** | Desktop | 1. Details | `docs/test-plan/screenshots/chrome_desktop_1280_details.png` | 1280 × 800 | 52,196 B | Populated source dropdown, balance ₹10,000.00, recipient `1000000003`, amount `500.00` |
| **Google Chrome 157** | Desktop | 2. Review | `docs/test-plan/screenshots/chrome_desktop_1280_review.png` | 1280 × 800 | 44,392 B | Step 2 active, review summary card with masked source `Savings (•••• 0001)`, recipient, amount |
| **Google Chrome 157** | Desktop | 3. Receipt | `docs/test-plan/screenshots/chrome_desktop_1280_receipt.png` | 1280 × 800 | 43,326 B | Step 3 active, confirmation card, reference `TRF-20261115-A1B2C3`, balance ₹9,500.00 |
| **Google Chrome 157** | Mobile | 1. Details | `docs/test-plan/screenshots/chrome_mobile_360_details.png` | 360 × 800 | 44,189 B | Single-column 360 px layout, fluid inputs, step 1 active, 0 px horizontal overflow |
| **Google Chrome 157** | Mobile | 2. Review | `docs/test-plan/screenshots/chrome_mobile_360_review.png` | 360 × 800 | 35,154 B | Step 2 active, review summary contained within 340 px card, 0 px horizontal overflow |
| **Google Chrome 157** | Mobile | 3. Receipt | `docs/test-plan/screenshots/chrome_mobile_360_receipt.png` | 360 × 800 | 34,808 B | Step 3 active, confirmation layout, Print Receipt and Make Another Transfer buttons |
| **Microsoft Edge 157** | Desktop | 1. Details | `docs/test-plan/screenshots/edge_desktop_1280_details.png` | 1280 × 800 | 52,164 B | Populated source dropdown, balance ₹10,000.00, recipient `1000000003`, amount `500.00` |
| **Microsoft Edge 157** | Desktop | 2. Review | `docs/test-plan/screenshots/edge_desktop_1280_review.png` | 1280 × 800 | 44,392 B | Step 2 active, review summary card with masked source `Savings (•••• 0001)`, recipient, amount |
| **Microsoft Edge 157** | Desktop | 3. Receipt | `docs/test-plan/screenshots/edge_desktop_1280_receipt.png` | 1280 × 800 | 43,326 B | Step 3 active, confirmation card, reference `TRF-20261115-A1B2C3`, balance ₹9,500.00 |
| **Microsoft Edge 157** | Mobile | 1. Details | `docs/test-plan/screenshots/edge_mobile_360_details.png` | 360 × 800 | 44,189 B | Single-column 360 px layout, fluid inputs, step 1 active, 0 px horizontal overflow |
| **Microsoft Edge 157** | Mobile | 2. Review | `docs/test-plan/screenshots/edge_mobile_360_review.png` | 360 × 800 | 35,154 B | Step 2 active, review summary contained within 340 px card, 0 px horizontal overflow |
| **Microsoft Edge 157** | Mobile | 3. Receipt | `docs/test-plan/screenshots/edge_mobile_360_receipt.png` | 360 × 800 | 34,808 B | Step 3 active, confirmation layout, Print Receipt and Make Another Transfer buttons |
| **Mozilla Firefox 159** | Desktop | 1. Details | `docs/test-plan/screenshots/firefox_desktop_1280_details.png` | 1366 × 683 | 42,814 B | Populated source dropdown, balance ₹10,000.00, recipient `1000000003`, amount `500.00` |
| **Mozilla Firefox 159** | Desktop | 2. Review | `docs/test-plan/screenshots/firefox_desktop_1280_review.png` | 1366 × 683 | 40,254 B | Step 2 active, review summary card with masked source `Savings (•••• 0001)`, recipient, amount |
| **Mozilla Firefox 159** | Desktop | 3. Receipt | `docs/test-plan/screenshots/firefox_desktop_1280_receipt.png` | 1366 × 683 | 36,950 B | Step 3 active, confirmation card, reference `TRF-20261115-A1B2C3`, balance ₹9,500.00 |
| **Mozilla Firefox 159** | Mobile | 1. Details | `docs/test-plan/screenshots/firefox_mobile_360_details.png` | 360 × 800 | 37,426 B | Single-column 360 px layout, Gecko normalized number input, 0 px horizontal overflow |
| **Mozilla Firefox 159** | Mobile | 2. Review | `docs/test-plan/screenshots/firefox_mobile_360_review.png` | 360 × 800 | 30,073 B | Step 2 active, review summary contained within 340 px card, 0 px horizontal overflow |
| **Mozilla Firefox 159** | Mobile | 3. Receipt | `docs/test-plan/screenshots/firefox_mobile_360_receipt.png` | 360 × 800 | 29,169 B | Step 3 active, confirmation layout, Print Receipt and Make Another Transfer buttons |

### Base Visual Screenshots (Maintained for Backward Compatibility)

| Screenshot File | Resolution | File Size | Description |
| :--- | :---: | :---: | :--- |
| `docs/test-plan/screenshots/chrome_desktop_1280.png` | 1280 × 800 | 52,196 B | Chrome 157 Desktop: Transfer interface (Details visual state) |
| `docs/test-plan/screenshots/chrome_mobile_360.png` | 360 × 800 | 44,189 B | Chrome 157 Mobile (360px): Verified zero horizontal overflow |
| `docs/test-plan/screenshots/edge_desktop_1280.png` | 1280 × 800 | 52,164 B | Edge 157 Desktop: Transfer interface (Details visual state) |
| `docs/test-plan/screenshots/edge_mobile_360.png` | 360 × 800 | 44,189 B | Edge 157 Mobile (360px): Fluid inputs and responsive step indicator |
| `docs/test-plan/screenshots/firefox_desktop_1280.png` | 1366 × 683 | 42,814 B | Firefox 159 Desktop: Gecko rendering with normalized spin buttons |
| `docs/test-plan/screenshots/firefox_mobile_360.png` | 360 × 800 | 37,426 B | Firefox 159 Mobile (360px): Normalized amount input and touch targets |

---

## 6. Defects Discovered and Resolved

1. **Step Indicator & Form Controls Horizontal Overflow at 360 px:**
   - *Reviewer Feedback:* "The 360px screenshot still shows clipping on the right edge of the step indicator. The `.step-divider` and `.step-title` push the container beyond 360px viewport."
   - *Root Cause:* Two issues caused overflow: (1) `.steps-indicator` had fixed `14px` divider and unconstrained text widths pushing total indicator to ~366px; (2) unauthenticated `.demo-controls` placed inputs and button horizontally side-by-side (`flex: 1 1 120px` + button) exceeding 360px.
   - *Fix:* In `frontend/transfer.html`:
     - Added global `html, body { max-width: 100%; overflow-x: hidden; }`.
     - Added `overflow-x: clip; max-width: 100%; box-sizing: border-box;` to `main` and `.card`.
     - Scaled `.steps-indicator` layout at `@media (max-width: 480px)` and `@media (max-width: 380px)`: `justify-content: space-between`, step numbers scaled to 22px/20px, dividers `min-width: 4px; max-width: 12px; flex: 1 1 6px`, text labels `white-space: nowrap; font-size: 0.68rem;`. Total width ~232px comfortably fits within 316px available card width.
     - Added `@media (max-width: 480px)` column-stacking to `.demo-controls`: inputs and buttons stack vertically with 100% width.
   - *Verification:* Measured `scrollWidth === 360px`, `clientWidth === 360px`. Pixel scan of column $x=359$ confirms zero clipped controls.
2. **Clarification of Visual-State Evidence vs. Transaction Evidence:**
   - *Reviewer Feedback:* "Please provide screenshot evidence of authenticated state (showing masked account and actual transfer form) across all three browsers..."
   - *Resolution:* Captured 18 visual-state screenshots displaying masked accounts, populated transfer forms, review cards, and receipt cards across all three browsers and both viewports. Clarified in documentation that these screenshots serve as visual layout evidence and not backend-persisted transaction proof.
3. **Firefox Version Alignment:**
   - *Reviewer Feedback:* "Firefox 146 is listed as PASS in the matrix, but the test report says Firefox 147 was tested. Please align the documentation with actual test results."
   - *Fix:* Directly probed the installed Firefox binary via capabilities (`Firefox 159.0`). The compatibility matrix was updated to strictly list `Firefox 159.0` as PASS, while marking the uninstalled prior version (`Firefox 146.x` / $n-1$) as PENDING.
4. **Receipt Print Clutter:**
   - *Defect:* `window.print()` included navigation headers, session login boxes, and transfer action buttons.
   - *Fix:* Added `@media print` rules hiding `.demo-bar`, `header`, `.steps-indicator`, `.page-title-area`, and `.btn-group`.
5. **Touch Target Sizing:**
   - *Defect:* `.btn-chip` buttons had 26px height, below recommended mobile touch targets.
   - *Fix:* Added `min-height: 36px` and responsive touch padding for screens $\le 480$px.

---

## 7. Remaining Actions & Pull Request Targeting

1. **Prior Minor Versions ($n-1$):**
   - Verification for Chrome 155, Edge 155, and Firefox 146 remains pending access to an external device laboratory (BrowserStack or SauceLabs) or a dedicated multi-version CI pipeline.
2. **Pull Request Target:**
   - Because `feature/US-15-browser-compatibility` branched from `feature/US-14-fund-transfer-usability`, PR #61 targets `feature/US-14-fund-transfer-usability` until PR #60 merges into `main`.
