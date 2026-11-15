# Customer history and CSV statements

Owner: Ronit (Member 3). Part of #8 (US-20) and #14 (US-21).

## Scope and dependencies

Merge after #63 and #64. This branch includes #64's API and current main;
it adds the customer landing page expected by the shared login introduced in #62.
It does not incorporate #65's performance-evidence commits. Refresh the final
load evidence after all application changes have merged.

The customer signs in at `/ui/index.html` and reaches `/ui/customer.html`.
The page uses the existing `bms_token` session and shared Customer/temporary-password
guard. It shows owned masked accounts, balance and status, latest 10 transactions,
date-range history in pages of 25, and a CSV statement for the selected dates.
Dates and displayed transaction times use IST. Download covers the entire range,
independently of which history page is visible. Unsupported PDF export is not
offered; the existing CSV/PDF requirement remains subject to the final deviations
record rather than being silently rewritten.

The page provides loading, empty, validation and error states, accessible labels,
live status messages, disabled duplicate-action controls, pagination boundaries,
and account-switch protection against stale asynchronous responses. At narrow
widths the table scrolls inside its own labeled, keyboard-focusable region.
Server values are rendered as text. Decimal money strings are grouped without
floating-point conversion, preserving paise on large amounts.

## Small additive account contract change

`GET /accounts` adds `account_id` to each existing masked account object. It never
returns the full number. Vijay's account router receives this single additive field;
its opening-account implementation is otherwise unchanged. Preserve this field
when resolving other account-router branches.

The following Customer-only routes resolve that ID with an ownership-filtered
query before delegating to the existing history/CSV implementation:

- `GET /accounts/by-id/{account_id}/transactions`
- `GET /accounts/by-id/{account_id}/statement`

An ID is an identifier, not authorization. Another customer's ID and a nonexistent
ID both return 404. Authentication, role restrictions and temporary-password
restrictions still run. Original full-number API routes remain available.
The statement wrapper retains #64's mandatory durable audit: audit failure returns
503 JSON without a CSV body or attachment header.

## Coordination

- Vijay: retain `account_id` in account listing, and preserve `/ui/customer.html`
  when integrating #60's transfer flow with the shared session. The transfer flow
  still needs a visible entry point after it is integrated; this PR does not link
  customers to an unmerged standalone transfer page.
- Password reset: shared login continues to direct temporary-password users to
  `/ui/change-password.html`. That page and the corrected #66 flow remain separate
  work; these guards are not bypassed here.
- Vaibhav: #56's notification-reading endpoint and its UI are separate scope.
- Release: #61 still needs its requested browser/version acceptance evidence.
  A single Edge run here does not prove the latest-two-versions browser matrix.

## Automated verification

Local verification on 15 November 2026: full pytest suite **218 passed, 1 warning**
(the existing Starlette/httpx deprecation). Headless Edge **157.0.4341.46** passed
all **11** browser scenarios. At a 360px viewport, document client/scroll widths
were both 360px; the table's scroll-region right edge was 335px. Desktop and mobile
screenshots were visually inspected. Evidence is under
[`test-plan/customer-ui/`](test-plan/customer-ui/). This is local verification;
GitHub CI is separate and must pass on the pushed head before merging.

`tests/test_customer_activity_ui.py` exercises real authentication, account listing,
latest-10 history, paginated history, a complete 31-row CSV, masking, account ownership,
role/temporary-password restrictions, invalid dates, empty history, and failed audits.
Existing history tests continue to cover 1,500-transaction complete exports.
The shared Node checks include large-decimal display. UI safety checks cover the
new page and JavaScript as well as existing static files.

## Optional reproducible browser check

Use a disposable SQLite file and an isolated server. The seeder refuses any existing
file. Synthetic balances/rows here are for interface checks, not ledger reconciliation
or performance evidence. Do not run against the project database or a shared server.

From the repository root, using an environment with the application/test requirements:

```powershell
$uiDb = Join-Path $env:TEMP ('bms-ui-' + [guid]::NewGuid().ToString('N') + '.db')
$env:BMS_DATABASE_URL = 'sqlite:///' + ($uiDb -replace '\\', '/')
python -B -m tests.ui.seed_customer_browser
python -B -m uvicorn app.main:app --host 127.0.0.1 --port 8769
```

In a second terminal, with Playwright available to Node (use an external tools
environment; no Node dependency is needed to serve the application):

```powershell
$env:BMS_UI_TEST_URL = 'http://127.0.0.1:8769'
$env:BMS_UI_BROWSER = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
node tests/ui/customer_browser_check.js
```

The browser test launches a disposable headless session, uses only synthetic users,
checks real login/history/export, then intercepts requests for error/race tests.
It writes screenshots and `browser-results.json` under the temporary
`bms-customer-ui-evidence` directory (override with `BMS_UI_EVIDENCE`). It does not
record tokens or real credentials. The synthetic password is defined in the test
factory. Stop only this test server with Ctrl+C afterward.
