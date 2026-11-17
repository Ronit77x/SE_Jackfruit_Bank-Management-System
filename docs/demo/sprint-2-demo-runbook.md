# Sprint 2 demo record

This document records the completed Sprint 2 demonstration and its evidence. It
is not a substitute for the release decision or for outstanding acceptance
verification. The demonstration used isolated disposable data; no credentials,
encryption keys or private local paths are part of this record.

## Recording and publication

- **Recording owner:** Vaibhava L. (Member 4)
- **Recording date:** 16 November 2026
- **Repository artifact:** [sprint2-demo.mp4](sprint2-demo.mp4)
- **Added to the submission branch:** 17 November 2026
- **Repository upload and PR merge coordination:** Ronit

The repository copy is named `sprint2-demo.mp4`. Its size is **13,322,370
bytes** and its MP4 container duration is approximately **270.90 seconds**
(4 minutes 31 seconds). The received file was copied without re-encoding;
its SHA-256 is `06ba4731df487dca24202f3aa1f3a42196c26df70b1061bd651b7345efc67966`.
This is longer than the assignment's two-minute Sprint 2 video length; no
assessor waiver is claimed. Recording credit remains with Vaibhava L.
The source file is preserved separately.

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

## Release reference

The video is included alongside this record as [sprint2-demo.mp4](sprint2-demo.mp4)
and linked from the main README. The final release documentation should retain
that artifact link and the outstanding verification limitations above. Adding
the recording does not establish acceptance of the unverified requirements.
