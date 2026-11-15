# Sprint 2 demo runbook

This runbook describes the workflows currently integrated on `main` and the
flows that must wait for open team PRs. It is a rehearsal guide, not evidence
that a demo was recorded or published. Use disposable seeded data and never
include real credentials, customer data or tokens in the recording.

## Before recording

1. Confirm the application is running in an isolated environment and `GET
   /health` returns HTTP 200.
2. Set a disposable `BMS_DATA_KEY`, seed a disposable database, and use two
   browser windows or contexts for Admin/Teller and Customer roles.
3. Record the browser version, commit SHA, environment and any unavailable
   workflow. Do not record the live US-30 monitor or its CSV.

## Integrated on current main

1. **Admin login and role restriction** — log in as `admin1`, show the Admin
   page, then demonstrate logout and that a non-Admin session cannot use it.
2. **Teller management** — create a Teller with a temporary password, show the
   returned user ID, and demonstrate deactivate/unlock through the Admin UI.
3. **Teller first login** — use the created Teller account and complete the
   mandatory password change flow.
4. **Cash operations** — from the Teller Cash page, perform a disposable
   deposit and withdrawal and show the receipt/balance messages.
5. **Customer overview/history** — log in as a Customer, show owned accounts,
   latest activity, IST date-range history and the statement-download control.
6. **Admin audit log** — load entries, filter by user/action/date, and show the
   fixed `Time (IST)` rendering and safe details display.
7. **Admin daily report** — generate a selected bank date and show deposits,
   opening-deposit breakdown, withdrawals, transfers and `Asia/Kolkata`.
8. **Health endpoint** — show `GET /health` returning HTTP 200.

## Dependent or separate work

- Teller account opening, existing-customer account opening, customer/account
  search and customer contact updates depend on the Teller Accounts UI work in
  the team PR chain (#60/#61). The current main branch references the Teller
  Accounts destination but does not contain that page; do not present it as an
  integrated UI workflow.
- Customer fund transfer is implemented at the API level but the final demo
  flow should wait for the team’s integration of PR #60 and its dependent UI.
- Admin freeze/unfreeze/close controls are in separate follow-up PR #81 and
  must not be shown as merged until that PR is reviewed and merged.
- Full November availability evidence depends on the observation period ending
  November 30, 2026; the current monitor sample is not a monthly result.

## Final checks before publication

- Verify every displayed workflow against the current main/integrated commit.
- Include role restrictions, logout and `/health` in the recording.
- State the remaining team dependencies and verification limitations.
- The user must record and publish the final Sprint 2 video after integration;
  this repository change does not claim a video URL or publication.
