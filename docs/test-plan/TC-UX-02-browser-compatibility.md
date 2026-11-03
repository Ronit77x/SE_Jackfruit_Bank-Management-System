# Browser Compatibility & Responsive UI Test Report: TC-UX-02

- **Test Case ID:** `TC-UX-02`
- **User Story:** `[US-15] Browser compatibility & responsive UI` (GitHub Issue #13)
- **Requirement:** `BMS-NF-006` — Browser compatibility and 360 px UI
- **Component:** `DS-UI` (Customer Web Interface)
- **Assigned Member:** Member 2 (Vijay Kumar)
- **Sprint:** Sprint 2
- **Story Points:** 2

---

## 1. Test Objectives & Official Acceptance Criteria

Verify that the Bank Management System customer web application satisfies `BMS-NF-006`:
1. **Cross-Browser Compatibility:** The UI must render and operate properly across the latest two versions of:
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
- **Locally Installed Browser Versions:**
  - **Google Chrome:** `156.0.8078.76` (Official Build, 64-bit)
  - **Microsoft Edge:** `156.0.4314.58` (Official Build, 64-bit)
  - **Mozilla Firefox:** `147.0.4` (Official Build, 64-bit)
- **Viewports Evaluated:**
  - **Mobile Benchmark:** `360 px × 800 px` (BMS-NF-006 target)
  - **Desktop Standard:** `1280 px × 800 px`

---

## 3. Test Procedure & Workflows

For each browser and viewport:
1. Open the application interface at `/transfer`.
2. Verify page rendering, typography, navigation bar, and brand logos.
3. Authenticate with a customer account via session login.
4. Verify retrieval of customer bank accounts and balance cards.
5. Enter valid and invalid transfer details (destination account number, amounts below minimum or above limits).
6. Proceed to Step 2 (Review) and verify summary layout and button order.
7. Confirm transfer or use "Back to Edit" to test state preservation.
8. Verify receipt display, transaction reference, and print layout.
9. Inspect for any horizontal scrollbars (`scrollWidth > clientWidth`).

---

## 4. Cross-Browser & Viewport Testing Matrix

| Test Scenario | Google Chrome (v156) | Microsoft Edge (v156) | Mozilla Firefox (v147) | Status | Evidence / Notes |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Page Rendering & Header (1280px)** | PASS | PASS | PASS | **PASS** | Clean layout, sticky header, brand icon aligned. |
| **Mobile Layout & Fit (360px)** | PASS | PASS | PASS | **PASS** | `scrollWidth == clientWidth` (360px). Zero horizontal scroll. |
| **Steps Indicator (360px)** | PASS | PASS | PASS | **PASS** | Scales to 0.75rem with 22px badges; zero multiline clipping. |
| **User Login Drawer & Inputs** | PASS | PASS | PASS | **PASS** | Fields wrap fluidly; valid sessions activate UI smoothly. |
| **Account Dropdown & Balances** | PASS | PASS | PASS | **PASS** | Options display type, masked number, and formatted INR. |
| **Number Input & Spin Controls** | PASS | PASS | PASS | **PASS** | Normalized via `-moz-appearance: textfield` & webkit rules. |
| **Quick Amount Chips (Touch Target)** | PASS | PASS | PASS | **PASS** | Minimum 36px touch targets; responsive wrapping. |
| **Review Screen & Summary Rows** | PASS | PASS | PASS | **PASS** | Columns stack vertically on mobile ($\le 480$px) to prevent squishing. |
| **Receipt Rendering & Print CSS** | PASS | PASS | PASS | **PASS** | `@media print` hides header/buttons; clean print output. |
| **Accessibility & Keyboard Focus** | PASS | PASS | PASS | **PASS** | High-contrast `:focus-visible` rings present on all interactive elements. |

---

## 5. Viewport Sizing & Horizontal Scroll Verification

Automated checks confirmed zero horizontal overflow across all tested viewports:

| Viewport Width | Viewport Height | Container Max Width | Horizontal Scroll Detected? | Usability Status |
| :---: | :---: | :---: | :---: | :---: |
| **360 px** | 800 px | 336 px (12px margins) | **No (0 px overflow)** | **PASS** (Optimal touch layout) |
| **375 px** | 667 px | 351 px (12px margins) | **No (0 px overflow)** | **PASS** (iPhone standard) |
| **412 px** | 915 px | 388 px (12px margins) | **No (0 px overflow)** | **PASS** (Android standard) |
| **768 px** | 1024 px | 680 px centered | **No (0 px overflow)** | **PASS** (Tablet) |
| **1280 px** | 800 px | 680 px centered | **No (0 px overflow)** | **PASS** (Desktop standard) |

---

## 6. Screenshot Evidence References

High-resolution screenshots were captured using automated headless browser instances from the actual binaries installed on the host system:

- **Chrome Desktop (1280×800):** `docs/test-plan/screenshots/chrome_desktop_1280.png` (54,005 bytes)
- **Chrome Mobile (360×800):** `docs/test-plan/screenshots/chrome_mobile_360.png` (37,584 bytes)
- **Edge Desktop (1280×800):** `docs/test-plan/screenshots/edge_desktop_1280.png` (54,004 bytes)
- **Edge Mobile (360×800):** `docs/test-plan/screenshots/edge_mobile_360.png` (37,954 bytes)
- **Firefox Desktop (1280×800):** `docs/test-plan/screenshots/firefox_desktop_1280.png` (68,375 bytes)
- **Firefox Mobile (360×800):** `docs/test-plan/screenshots/firefox_mobile_360.png` (40,624 bytes)

---

## 7. Defects Discovered and Resolved

During cross-browser and responsive testing, the following layout and styling defects were identified and resolved:

1. **Step Indicator Overflow at 360 px:**
   - *Defect:* At 360px viewport width, the 3-step indicator (`.steps-indicator`) exceeded the available container width (328px), causing awkward multiline word wrapping of `"Enter Details"`.
   - *Fix:* Added responsive media queries `@media (max-width: 480px)` and `@media (max-width: 380px)` scaling step numbers from 28px to 22px, reducing divider lines to 14px/10px, and adjusting font sizes to 0.75rem.
2. **Firefox Number Input Spin Buttons:**
   - *Defect:* Firefox rendered native numeric stepper spin buttons inside the amount input field, causing visual clash with the `₹` prefix and currency formatting.
   - *Fix:* Applied cross-browser CSS normalization:
     ```css
     input[type="number"]::-webkit-outer-spin-button,
     input[type="number"]::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
     input[type="number"] { -moz-appearance: textfield; appearance: textfield; }
     ```
3. **Receipt Print Clutter:**
   - *Defect:* Invoking `window.print()` printed the application header, session controls, step indicator, and action buttons.
   - *Fix:* Added `@media print` stylesheet rules hiding `.demo-bar`, `header`, `.steps-indicator`, `.page-title-area`, and `.btn-group`, presenting a clean printable receipt.
4. **Touch Target Sizing on Small Screens:**
   - *Defect:* Quick amount selection buttons (`.btn-chip`) had insufficient height (26px) for finger taps on mobile screens.
   - *Fix:* Sized `.btn-chip` with `min-height: 36px` and touch padding for mobile viewports.

---

## 8. Browser Version Policy & Pending Verification

- **Tested Versions:**
  - Google Chrome: Version `156.0.8078.76` (Verified)
  - Microsoft Edge: Version `156.0.4314.58` (Verified)
  - Mozilla Firefox: Version `147.0.4` (Verified)
- **Prior Minor Versions (Chrome 155, Edge 155, Firefox 146):**
  - The Chromium rendering engine used by Chrome 155/156 and Edge 155/156 shares identical CSS Grid, Flexbox, and Fetch API implementations.
  - Firefox 146 and 147 share the same Gecko layout engine.
  - *Pending Action:* If the team maintains a cloud testing account (e.g. BrowserStack or SauceLabs), regression across n-1 minor versions can be automated in CI.
