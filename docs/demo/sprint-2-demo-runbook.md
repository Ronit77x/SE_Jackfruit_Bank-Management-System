# Sprint 2 demo record

This document records the completed Sprint 2 demonstration and its evidence. It
is not a substitute for the release decision or for outstanding acceptance
verification. The demonstration used isolated disposable data; no credentials,
encryption keys or private local paths are part of this record.

## Recording and publication

- **Recording owner:** Vaibhava L. (Member 4)
- **Recording date:** 16 November 2026
- **Edited artifact:** `BMS_Sprint2_Demo_Final_Edited.mp4`
- **Publication owner:** Ronit
- **Publication status:** Pending Ronit's publication
- **Published URL:** Not available yet

The edited video is approximately 4 minutes 31 seconds long, slightly above the
four-minute target. It is an H.264 video at
1838×1630. The verified local file size is 13,328,429 bytes. The available
macOS metadata identifies it as video-only; no audio stream is reported. The
file remains in Downloads and is not committed to Git. The source recordings
remain preserved separately.

## Demonstrated workflows

### Admin

- Admin authentication and dashboard.
- Teller creation and management.
- Account freeze and unfreeze.
- Audit log retrieval and filtering.
- Daily transaction reporting, showing deposits, withdrawals and transfers.
- Health endpoint.

The backend daily-report API has an opening-deposits breakdown, but the current
Admin UI does not display that breakdown; it was not claimed as a demonstrated
UI feature. Account closure was intentionally not demonstrated because it is
irreversible.

### Teller

- New Teller login.
- Mandatory first-login password change.
- Cash deposit.
- Successful withdrawal.
- Rejected withdrawal due to minimum-balance protection.
- Customer and account search.
- Opening an account for a new customer.
- Opening another account for an existing customer.
- Updating customer contact information.

### Customer

- Customer login and mandatory password change.
- Account overview.
- Savings and Current accounts.
- Transaction history.
- Fund transfer Details, Review and Receipt workflow.

## Integration status

The demonstrated workflows rely on these merged PRs:

- [PR #60](https://github.com/SEMiniProjectBMS/SE_Jackfruit_Bank-Management-System/pull/60) — Fund Transfer Usability implementation.
- [PR #61](https://github.com/SEMiniProjectBMS/SE_Jackfruit_Bank-Management-System/pull/61) — Browser Compatibility and Responsive UI implementation.
- [PR #79](https://github.com/SEMiniProjectBMS/SE_Jackfruit_Bank-Management-System/pull/79) — Teller Accounts UI.
- [PR #81](https://github.com/SEMiniProjectBMS/SE_Jackfruit_Bank-Management-System/pull/81) — Admin account freeze/unfreeze/close controls.

These implementations are integrated; none is described as pending here.

## Test evidence

The isolated demonstration workspace completed this local command:

```text
python -m pytest -q
447 passed, 1 skipped, 0 failed, 1 warning
approximately 45 seconds
```

The warning was a `StarletteDeprecationWarning` stating that using httpx with
`starlette.testclient` is deprecated and that `httpx2` should be installed.
It is a deprecation warning, not a test failure. This is local recorded
evidence, not a new GitHub Actions result or a claim that CI was rerun.

## Outstanding acceptance and release limitations

- **Issue #12 / US-14 usability:** remains open. Five genuine first-time
  participants are required; zero completed human trials are recorded. The
  implemented transfer workflow and automated checks do not satisfy that human
  usability criterion. No pass rate or waiver is claimed.
- **Issue #13 / US-15 browser compatibility:** is open and has been reopened.
  Latest-two-version browser verification and physical touchscreen testing
  remain outstanding. Merged implementation PR #61 does not make every
  acceptance criterion complete.
- November monthly availability evidence remains incomplete; the health
  endpoint or a short local sample is not a complete monthly result.
- External/deployed HTTPS verification remains outstanding; local HTTPS checks
  do not establish production deployment evidence.
- Retention-period and backup/disaster-recovery verification remain
  outstanding.

PR #45 (deviations documentation), PR #68 (final documentation/release freeze)
and PR #84 (release readiness documentation) remain open. The completed demo
record should now be referenced in the release documentation. The team has not
identified #68 or #84 as the authoritative final documentation PR in this
record; the team should decide that during review. This runbook does not merge,
close or otherwise change those PRs.

## Follow-up

Ronit should publish the edited artifact and provide the actual public URL.
After that URL is available, update the README and release documentation with
the verified publication reference and status. Until then, no public URL is
claimed and no local Downloads path should be used as one.
