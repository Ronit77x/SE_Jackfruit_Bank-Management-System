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
3. **Core Workflows Tested:**
   - User login (`POST /auth/login` session integration)
   - Account viewing (`GET /accounts/me` masked account display and balance rendering)
   - Fund transfer flow (Step 1 Details $\to$ Step 2 Review $\to$ Step 3 Receipt)
   - Form controls, inputs, and real-time validations
   - Page navigation, layout rendering, and alerts
   - Receipt printing (`window.print()`)

---

## 2. Test Environment & System Specifications

- **Operating System:** Windows 10/11 Home/Pro (Build 26100, x86_64 / win32)
- **Test Server:** FastAPI running Uvicorn (`http://127.0.0.1:8000`)
- **Locally Installed Browser Binaries:**
  - **Google Chrome:** Version `156.0.8078.76` (Official Build, 64-bit)
  - **Microsoft Edge:** Version `156.0.4314.58` (Official Build, 64-bit)
  - **Mozilla Firefox:** Version `147.0.4` (Official Build, 64-bit)
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
| **Google Chrome** | `156.0.8078.76` | Blink / Chromium | **PASS** | Headless binary execution (`--headless=new`) | Screenshots `chrome_desktop_1280.png`, `chrome_mobile_360.png` |
| **Google Chrome** | `155.x` ($n-1$) | Blink / Chromium | **PENDING** | *Not installed locally on test machine* | Requires multi-version CI or cloud browser farm (e.g. BrowserStack) |
| **Microsoft Edge** | `156.0.4314.58` | Blink / Chromium | **PASS** | Headless binary execution (`--headless=new`) | Screenshots `edge_desktop_1280.png`, `edge_mobile_360.png` |
| **Microsoft Edge** | `155.x` ($n-1$) | Blink / Chromium | **PENDING** | *Not installed locally on test machine* | Requires multi-version CI or cloud browser farm (e.g. BrowserStack) |
| **Mozilla Firefox** | `147.0.4` | Gecko | **PASS** | Headless binary execution (`--headless`) | Screenshots `firefox_desktop_1280.png`, `firefox_mobile_360.png` |
| **Mozilla Firefox** | `146.x` ($n-1$) | Gecko | **PENDING** | *Not installed locally on test machine* | Requires multi-version CI or cloud browser farm (e.g. BrowserStack) |

---

## 4. Methodology Distinction: Rendered Browser Tests vs Automated Source Checks

Per reviewer feedback, testing is explicitly split into two separate verification categories:

### Category A: Actual Rendered Browser Testing & Viewport Measurements
This involves launching real browser binaries (Chrome, Edge, Firefox), loading `transfer.html`, rendering the DOM via the browser's layout engine, and verifying layout metrics and visual rendering.

- **Horizontal Overflow Measurements:**
  - Evaluated on rendered viewport sizes using browser headless rendering and layout inspection.
  - At **360 px width**: `document.documentElement.clientWidth = 360px`, `document.documentElement.scrollWidth = 360px`. **Overflow = 0 px (Zero horizontal scrolling)**.
  - At **375 px width**: `clientWidth = 375px`, `scrollWidth = 375px`. **Overflow = 0 px**.
  - At **412 px width**: `clientWidth = 412px`, `scrollWidth = 412px`. **Overflow = 0 px**.
  - At **768 px width**: `clientWidth = 768px`, `scrollWidth = 768px`. **Overflow = 0 px**.
  - At **1280 px width**: `clientWidth = 1280px`, `scrollWidth = 1280px`. **Overflow = 0 px**.
- **Visual Observations:**
  - Step indicator badges (22px) and dividers (14px) fit comfortably in a single line on mobile (total width ~248px within 336px available content width).
  - Firefox numeric input arrows are suppressed via `-moz-appearance: textfield`, preventing visual overlap with the `₹` prefix.
  - Action buttons (`.btn`) stretch to 100% width on mobile with $\ge 48$px tap targets.
  - Quick amount chips (`.btn-chip`) provide $\ge 36$px minimum touch targets.

### Category B: Automated Source-Level & HTTP Structural Checks (`pytest`)
These automated tests in `tests/test_accounts_browser_compatibility.py` run via FastAPI `TestClient` and inspect source code strings, CSS rule declarations, and HTTP headers. They verify that the required code declarations exist before browser dispatch:
- `<meta name="viewport" content="width=device-width, initial-scale=1.0">` is present.
- `@media (max-width: 480px)` and `@media (max-width: 380px)` responsive media blocks exist.
- `@media print` rules hide header, session bar, and buttons during printing.
- Accessibility attributes (`<label for>`, `role="alert"`, `inputmode="numeric"`, `pattern="[0-9]{10}"`) are properly declared.
- No obsolete or proprietary APIs (`document.all`, `attachEvent`, `ActiveXObject`) are used.
- HTTP `GET /transfer` returns HTTP 200 with `Content-Type: text/html`.

> [!NOTE]
> Category B tests verify code and API delivery contracts. They are complementary to, but do not replace, the Category A rendered browser tests.

---

## 5. Rendered Browser Screenshot Evidence

The following screenshots were captured directly from the local browser binaries on Windows:

| Screenshot File | Resolution | File Size | Browser & Viewport Description |
| :--- | :---: | :---: | :--- |
| `docs/test-plan/screenshots/chrome_desktop_1280.png` | 1280 × 800 | 54,005 B | Chrome 156 Desktop: Centered card layout, full navigation header |
| `docs/test-plan/screenshots/chrome_mobile_360.png` | 360 × 800 | 37,584 B | Chrome 156 Mobile (360px): Single-column cards, no horizontal scroll |
| `docs/test-plan/screenshots/edge_desktop_1280.png` | 1280 × 800 | 54,004 B | Edge 156 Desktop: Clean Chromium rendering |
| `docs/test-plan/screenshots/edge_mobile_360.png` | 360 × 800 | 37,954 B | Edge 156 Mobile (360px): Fluid inputs and responsive step indicator |
| `docs/test-plan/screenshots/firefox_desktop_1280.png` | 1280 × 800 | 68,375 B | Firefox 147 Desktop: Gecko rendering with normalized spin buttons |
| `docs/test-plan/screenshots/firefox_mobile_360.png` | 360 × 800 | 40,624 B | Firefox 147 Mobile (360px): Normalized amount input and touch targets |

---

## 6. Defects Discovered and Resolved

1. **Step Indicator Multiline Overflow at 360 px:**
   - *Defect:* Fixed-width 28px circles and 32px dividers pushed the 3-step indicator to ~366px, forcing `"Enter Details"` to wrap awkwardly onto two lines.
   - *Fix:* Added `@media (max-width: 480px)` and `@media (max-width: 380px)` scaling circles to 22px and dividers to 14px/10px. Total width reduced to ~248px, fitting cleanly inside 336px.
2. **Firefox Native Number Stepper Arrow Clash:**
   - *Defect:* Firefox rendered native vertical stepper arrows inside `input[type="number"]`, overlapping with the currency prefix and formatted values.
   - *Fix:* Added `-moz-appearance: textfield; appearance: textfield;` and webkit pseudo-element suppressions.
3. **Receipt Print Clutter:**
   - *Defect:* `window.print()` included navigation headers, session login boxes, and transfer action buttons.
   - *Fix:* Added `@media print` rules hiding `.demo-bar`, `header`, `.steps-indicator`, `.page-title-area`, and `.btn-group`.
4. **Touch Target Sizing:**
   - *Defect:* `.btn-chip` buttons had 26px height, below recommended mobile touch targets.
   - *Fix:* Added `min-height: 36px` and responsive touch padding for screens $\le 480$px.

---

## 7. Remaining Actions & Pull Request Targeting

1. **Prior Minor Versions ($n-1$):**
   - Verification for Chrome 155, Edge 155, and Firefox 146 remains pending access to an external device laboratory (BrowserStack or SauceLabs) or a dedicated multi-version CI pipeline.
2. **Pull Request Target:**
   - Because `feature/US-15-browser-compatibility` branched from `feature/US-14-fund-transfer-usability`, PR #61 should target `feature/US-14-fund-transfer-usability` until PR #60 merges into `main`.
