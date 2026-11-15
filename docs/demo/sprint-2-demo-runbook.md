# Sprint 2 demo runbook

This runbook describes the workflows currently integrated on `main` and the
flows that must wait for open team PRs. It is a rehearsal guide, not evidence
that a demo was recorded or published. Use disposable seeded data and never
include real credentials, customer data or tokens in the recording.

**Sprint 2 recording owner: Vaibhava L. (Member 4).**

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
5. **Teller Accounts** — using the UI merged through PR #79, demonstrate Teller
   account opening for a new customer, opening another account for an existing
   customer, customer/account search and customer contact updates.
6. **Customer overview/history** — log in as a Customer, show owned accounts,
   latest activity, IST date-range history and the statement-download control.
7. **Admin audit log** — load entries, filter by user/action/date, and show the
   fixed `Time (IST)` rendering and safe details display.
8. **Admin daily report** — generate a selected bank date and show the UI's
   deposits, withdrawals, transfers and `Asia/Kolkata` timezone. The backend
   API also returns `deposits.opening_deposits`, but the current Admin UI does
   not display that breakdown; do not present it as a UI feature.
9. **Health endpoint** — show `GET /health` returning HTTP 200.

## Dependent or separate work

- Teller Accounts UI is integrated through PR #79 and is included in the
  integrated workflow above.
- Customer fund transfer is implemented at the API level but the final demo
  flow should wait for the still-open PR #60 and its dependent UI. Browser
  compatibility PR #61 is also still open and based on that transfer work.
- US-27 browser security verification is integrated through merged PR #78.
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
