# Deviations and delivery status: Sprint 1 and Sprint 2

Updated: **17 November 2026**. Evidence baseline: main
`f3551eca0bf3285b514fc0d67cfc5bc9a7c783a8` after PR #83. The application
and benchmark evidence remain those reviewed after PR #65; PR #83 adds the
Sprint 2 demo record.

This record distinguishes implementation choices, late deliverables and unmet
or incompletely verified acceptance criteria. Recording a limitation does not
change the submitted SRS or establish that an assessor has waived it. Recording
dates and video artifact links are maintained in the release documentation.

## Delivery timeline deviation (both sprints)

The assignment's Part-2 deliverables specify **19–23 October 2026 for Sprint 1**
and **26–30 October 2026 for Sprint 2**. The project-board windows supplied by
the team were wider: 19–25 October and 26 October–1 November. Those board
windows do not revise or extend the assignment dates. Both planning records
are distinguished here so the overrun is measured against the submitted
assignment rather than silently replacing its deadlines.

Integration, corrective reviews, verification and demonstration work continued
through **17 November 2026**, beyond the planned windows. Sprint 1 demonstration
evidence is committed through PR #74. Vaibhava L. (Member 4) recorded the
Sprint 2 demonstration on **16 November 2026**; its documentation was integrated
through [PR #83](https://github.com/SEMiniProjectBMS/SE_Jackfruit_Bank-Management-System/pull/83)
on **17 November 2026**. Ronit reviewed and merged that PR. This merge role is
not a separate project deliverable or recording credit.

The [Sprint 2 demo record](demo/sprint-2-demo-runbook.md) was merged separately
from the video. The received MP4 has been copied without re-encoding to
`docs/demo/sprint2-demo.mp4` in the separate `docs/publish-sprint2-demo` branch,
with README and demo-record links, prepared on **17 November 2026**. The video
artifact must be merged before the final release references it as available on
main. Its measured duration is **270.90 seconds (4 minutes 31 seconds)**,
exceeding the assignment's two-minute Sprint 2 video length. This is a
presentation deviation; no assessor waiver is claimed.

The delivery overrun occurred while dependent branches were integrated, review
findings were resolved, and shared authentication, role-specific UI and
security/data-integrity checks were completed. The original plan did not
adequately allow for this integration and verification work before recording.
Dependency-ordered merges and regression checks were completed before
demonstrating the integrated application. This explains the observed work and
delay without blaming an individual or inventing an external event. Late
delivery remains a schedule deviation.

Final documentation/release review is tracked in PR #68 (US-07, issue #36).
Use the release documentation for actual demonstration dates and published
video artifact links; this deviations log records delivery and scope decisions.
The Part-2 assignment also requires deviations to be documented and explained
during the final demo. Reference the relevant entries in that explanation;
concise on-screen text can communicate the limitations in a silent recording.

## Sprint 1 implementation and presentation deviations

The original four entries were recorded on 22 October 2026; their current
disposition below was reviewed on 17 November 2026. The resolved withdrawal-day
entry additionally preserves the historical deviation and its correction.

| ID | Story / baseline | Observed implementation or presentation | Reason and current disposition |
|---|---|---|---|
| S1-01 | Sprint 1; SRS §3.1 and SAD §4.5 describe Customer, Teller and Admin browser screens | The Sprint 1 video uses FastAPI Swagger UI (`/docs`). Role-specific HTML screens were integrated in Sprint 2. | UI integration followed the backend foundation. This is a Sprint 1 sequencing/presentation deviation, not a claim that Swagger is the finished portal. Browser pages now exist through PRs #62, #75, #76, #77, #79, #81, #60 and #61. |
| S1-02 | US-17/18/19; SAD §4.3 account identifiers | Deposit/withdrawal `accountId` and transfer `fromAccount`/`toAccount` are ten-digit account-number strings, not internal database IDs. | Clarifies the identifier used for transactions. Owned-account history separately supports internal IDs without changing these payloads. |
| S1-03 | US-17/18/19; SAD §§4.3–4.4 error lists | Explicit outcomes include HTTP 404 `ACCOUNT_NOT_FOUND`, HTTP 400 `VALIDATION_ERROR`, and HTTP 400 `INVALID_TRANSFER` for same-account transfers. The standard response also contains a compatibility `detail` field. | Endpoint error lists were not exhaustive. The response retains `code`, `message`, `timestamp` and `traceId`, with understandable rejection messages and existing client compatibility. |
| S1-04 | US-17/18/19; SAD §4.3 monetary responses | Monetary values are decimal strings such as `"1500.00"`, rather than binary floating-point JSON numbers. | Preserves exact paise in transport. This representation choice does not relax transaction integrity. |
| S1-05 (resolved) | US-18; BR-02 daily withdrawal limit | The initial implementation counted daily withdrawals from UTC midnight rather than the bank's IST calendar-day boundary. | Corrected on **25 October 2026** in commit [`b31eb6d`](https://github.com/SEMiniProjectBMS/SE_Jackfruit_Bank-Management-System/commit/b31eb6de13bcf21e1973ca23f59baeb0b63f7a18), included in [PR #43](https://github.com/SEMiniProjectBMS/SE_Jackfruit_Bank-Management-System/pull/43), merged on 30 October 2026. IST midnight (UTC+05:30) is converted to UTC for the database query; dedicated IST-boundary regression tests verify BR-02 behavior. This historical deviation is resolved, not an outstanding limitation. |

## Sprint 2 acceptance deviations and verification limits

### S2-01 — First-time-user usability: minimum sample not met

**US-14, issue #12; BMS-NF-004; TC-UX-01; PR #60.** The original criterion is at
least five genuine first-time users, with at least `ceil(0.90 × n)` completing
an accurate transfer unaided within 120 seconds. Five users require five
successes.

**Submission decision, 16 November:** the five-participant trial will not be
completed for this submission. Recruitment is limited to two potential
independent first-time participants within the remaining testing window;
three additional participants are unavailable. This participant-availability
constraint is the reason for the reduced evaluation scope, not proof that the
target was met.

The committed observation sheet currently contains **zero completed human
trials**. Two available people must not be described as two tested people.
The transfer wizard, API/ledger tests and browser checks verify functionality,
not human usability acceptance.

If the two people are tested, record actual timings, assistance, accuracy and
feedback as an **exploratory two-person pilot**, reporting `x/2` observed
successes only. Even `2/2` does not satisfy the minimum sample or establish the
five-person acceptance result. Additional recruitment is not a prerequisite
for recording this submission limitation.

**Disposition: implementation complete; formal usability acceptance not met /
not verified.** The SRS threshold remains unchanged. Repeated attempts by one
person do not count as independent first-time users, and no observations or
pass rates are fabricated. Team review acknowledges the limitation; an
instructor/customer waiver is not claimed and must be recorded separately if
obtained. See the [protocol](test-plan/TC-UX-01-usability-test-protocol.md) and
[observation sheet](test-plan/TC-UX-01-observation-sheet.md).

### S2-02 — Browser coverage is partial

**US-15, issue #13; BMS-NF-006; TC-UX-02; PR #61.** Recorded authenticated
journeys cover Chrome 157.0.8103.51, Edge 157.0.4341.60, Firefox desktop 159.0,
and Playwright Firefox/Gecko 153.0 at 360px. The Gecko viewport run is not a
claim about the installed Firefox 159 desktop binary at a native 360px size.
Viewport emulation does not establish physical touchscreen compatibility.

PR #61 completes and integrates the US-15 implementation. An implementation-completion closure of issue #13
records that implementation completion; its tracker state does not establish
that the remaining verification has passed. Latest-two-browser-version coverage
and physical touchscreen testing are separate outstanding verification
activities, retained in the [browser report](test-plan/TC-UX-02-browser-compatibility.md).
The recorded environment covers only available binaries/engine versions, so
full BMS-NF-006 version coverage remains **unverified**. The original criterion
is unchanged; no unsupported `n-1` labels or blanket acceptance claim is made.
This clarification does not request reopening #13 or changing its completed
implementation.

### S2-03 — Monthly availability is not demonstrated

**US-30, issue #23; BMS-NF-002; TC-Ops-01; PRs #54 and #82.** The health
endpoint, monitor and analyzer exist. At this evidence baseline, the tracked
[uptime CSV](test-plan/uptime-log.csv) contains one successful observation on
2 November 2026 (HTTP 200, 22.85 ms), not a complete month. Later data must be
reported with its actual window, failures, gaps and maintenance treatment;
uncommitted monitoring data is not assessed here.

The local verification window is shorter than the complete November calendar
month, and no complete earlier-month log is supplied. Neither a smoke check
nor the load test proves 99.5% monthly availability. Scheduled-maintenance
exclusion is also unverified. The monthly target remains **unverified**;
implementation and measured samples are reported separately. See the
[monitoring instructions](test-plan/uptime-monitoring.md).

### S2-04 — Statement format clarification

**US-21; BMS-F-024; TC-Stmt-02; PRs #64 and #75.** Complete, date-filtered CSV
statement download and auditing are implemented; PDF export is not. The SRS
requirement says **CSV or PDF**, so CSV satisfies that format alternative.
Overview wording `CSV/PDF` must not be presented as both formats being
implemented. This is a scope clarification, not an invented failed criterion.

### S2-05 — HTTPS verification is local, not a production deployment

**US-27; BMS-SR-001 / BMS-SR-005; PRs #48, #72 and #78.** Recorded TLS 1.2/1.3
negotiation, legacy-protocol refusal, validation and output encoding apply to
the documented local Uvicorn HTTPS setup. The Nginx configuration was inspected
but not runtime-tested as a deployed reverse proxy. Public-CA deployment is
not evidenced. Local HTTP load-test results are not deployed HTTPS performance.
See the [security verification](security/us-27-verification.md).

### S2-06 — Audit retention verification boundary

**US-31; BMS-NF-005; TC-Aud-02; PRs #55 and #80.** Timestamped audit records,
database update/delete rejection and the five-year policy are verified; no
application purge job exists. This satisfies configuration/append-only
verification scope, but does not empirically prove five years of elapsed
storage or external backup/disaster-recovery retention. Those operational
claims remain unverified. See the
[audit record](security/US-31-audit-append-only-verification.md).

### S2-07 — Performance acceptance passed within the recorded workload

**US-22, issue #15; BMS-NF-001; TC-Perf-01; PRs #63 and #65.** The final test
uses 50 users over 120 seconds including ramp-up and login, on one workstation
over local HTTP. It records 8,569 requests, no failures and endpoint p95 values
of 61–62 ms, with source provenance and ledger reconciliation in the
[load-test report](test-plan/load-test-results.md).

The baseline does not specify a minimum steady-state duration. Its stated
50-user/p95 criterion is satisfied; this is **not** an unmet acceptance
criterion. Sustained production capacity, network/TLS overhead, other endpoints
and monthly availability are outside this evidence.

## Submission and issue disposition

- Issue #15 may be closed as **Completed**, linking the merged benchmark.
- If the team closes #12 because no further recruitment is planned, use
  **Not planned**, explain the implemented functionality and unmet acceptance,
  and link this record after review. Do not mark all criteria passed.
- Issue #13 may be closed for the implementation integrated through #61.
  Latest-two-browser-version and physical touchscreen verification remain
  outstanding in the browser report and this record; implementation closure
  does not claim those activities passed. No reopening is requested here.
- Issue #23's monthly target and #36's final release are not completed by this
  document. Keep their outstanding criteria visible.
- PR #45 requires normal team review. Approval acknowledges accurate reporting,
  not an external waiver of SRS acceptance criteria.
- Final release notes link this record and the actual video artifacts and
  dates, retaining unresolved verification limitations.
