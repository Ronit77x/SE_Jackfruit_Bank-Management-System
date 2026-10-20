# Software Requirements Specification (SRS) - Bank Management System

**Version:** 1.0 (Draft)  
**Status:** Draft for integration review; approval pending  
**Owner:** Tarini Arora - Member 1 (SRS owner and integration)  
**Team:** BMS_PES  
**Date:** 13 October 2026  
**Target path:** `docs/srs/SRS_BankManagementSystem_v1.0_DRAFT.md`

> This document specifies intended requirements. It does not claim features have been implemented, deployed or tested. Do not approve until Section 9 is resolved.

## Document Control

| Version | Date | Owner / contributor | Change summary | Approval |
|---|---|---|---|---|
| 1.0 - draft | 13 Oct 2026 | Member 1 - Tarini Arora | Integrated supplied Sections 4.2, 4.3, 4.4, Section 5/security/RTM; drafted Sections 1-3 and reconstructed Section 4.1 from RTM summaries; recorded open issues. | Pending review |

## Contents

1. [Introduction](#1-introduction)
2. [Overall Description](#2-overall-description)
3. [External Interface Requirements](#3-external-interface-requirements)
4. [System Features](#4-system-features)
5. [Non-functional and Security Requirements](#5-non-functional-and-security-requirements)
6. [Business Rules and Constraints](#6-business-rules-and-constraints)
7. [System Models and Diagrams](#7-system-models-and-diagrams)
8. [Requirements Traceability Matrix](#8-requirements-traceability-matrix-rtm)
9. [Integration Review Items](#9-integration-review-items)

## 1. Introduction

### 1.1 Purpose

This Software Requirements Specification (SRS) defines the functional, non-functional, security, interface and traceability requirements for the Bank Management System (BMS) software engineering mini-project. It provides a common baseline for design, implementation, testing and review. Requirements in this draft describe intended behaviour; they are not evidence that a feature has been implemented or verified.

### 1.2 Scope

The BMS is a web-based system for a single bank. It supports three user roles - Customer, Teller and Admin - and is intended to cover account opening and account information, cash deposits and withdrawals, internal BMS fund transfers, transaction history and downloadable statements, administrative Teller management, audit-log review, daily transaction reporting, and simulated debit/credit notifications.

Explicit exclusions in the supplied baseline are ATM functionality and real external SMS/e-mail gateway delivery. Notification events are written to a log. Transfers described in this SRS are between accounts within the BMS; external-bank transfer support is not specified in the supplied materials and must not be assumed.

### 1.3 Document conventions and terminology

- “Shall” identifies a mandatory requirement. Each requirement has a fixed identifier; requirement IDs from the supplied contributions are preserved.
- BMS - Bank Management System; SRS - Software Requirements Specification; RTM - Requirements Traceability Matrix; NFR - non-functional requirement.
- Customer - user who can view their own accounts, transfer funds, and view/download transaction history and statements.
- Teller - bank staff user who opens accounts, updates customer contact details, searches customers, and records cash deposits/withdrawals.
- Admin - staff role that manages Teller user accounts, changes account status, reviews audit logs and generates daily reports.
- ACID - atomicity, consistency, isolation and durability. REST/JSON - the stated web API interface style.
- Acceptance criteria and test identifiers describe planned verification. RTM status “N” means not started in the supplied draft; it does not mean a test passed.

### 1.4 References

- Repository `README.md`: SE_Jackfruit - Bank Management System (project scope, fixed technology baseline and repository structure).
- Shared BMS requirement/business-rule baseline v1.2, referenced in the Account Management contribution; the canonical file was not included in the materials pasted for this integration.
- `SRS_part_M2_Account.docx` - Member 2 contribution, Section 4.2 Account Management.
- `SRS_part_M3_Transactions.docx` - Member 3 transaction contribution, Section 4.3 Transactions.
- `SRS_part_M4_Admin_NFR_Security_RTM.docx` - Member 4 contribution, Section 4.4, Section 5, security objectives/requirements, use-case diagram description and RTM.
- `SAD_BankManagementSystem_v1.0.docx` / `.pdf` and `docs/diagrams/*` - architecture/design and diagram sources to be checked during cross-document review.
- `Test_Plan_BankManagementSystem_v1.0.docx` - planned test cases and verification methods; all cited test IDs must be cross-checked against this document.

## 2. Overall Description

### 2.1 Product perspective

The BMS is described as a layered web application. The fixed project technology baseline in the repository README is Python 3 with FastAPI for REST/JSON, SQLite accessed through SQLAlchemy, an HTML/CSS/JavaScript web interface, pytest for automated testing, and GitHub Actions for CI. This SRS does not introduce a different stack.

### 2.2 Product functions

- Authenticate users, establish sessions, lock accounts after repeated failed login attempts, enforce roles and support password change / first-login password change.
- Open Savings and Current accounts, maintain customer contact details, search customers, show a Customer their own account details and balance, and let Admins freeze, unfreeze or close accounts.
- Record deposits and withdrawals, transfer funds between eligible BMS accounts, show filtered transaction history and mini-statements, and provide CSV/PDF statement downloads.
- Allow Admins to create, deactivate and unlock Teller users, review filtered audit logs, and generate daily transaction summaries.
- Record simulated e-mail/SMS notification entries after debit or credit events, without a real external gateway.
- Apply performance, availability, integrity, usability, compatibility, audit-retention and security requirements stated in Sections 5 and 9.

### 2.3 User classes

| User class | Main responsibilities / permitted functions |
|---|---|
| Customer | View only their own account details and balance; transfer funds from their account to another eligible BMS account; view transaction history and download statements; receive a simulated notification record after debit/credit activity. |
| Teller | Open Savings/Current accounts; update customer phone, e-mail and address; search customers; record eligible deposits and withdrawals. |
| Admin | Create, deactivate and unlock Teller user accounts; freeze, unfreeze or close accounts subject to the balance rule; review filtered audit logs; generate daily transaction summaries. |

The system must enforce these permissions on the server, not only through UI controls. The full permission matrix must remain consistent across this SRS, the SAD and the test plan.

### 2.4 Operating environment

- Backend/API: Python 3 and FastAPI, with REST/JSON interfaces.
- Database: SQLite through SQLAlchemy.
- Client: HTML, CSS and JavaScript in a browser; compatibility target is the latest two versions of Chrome, Edge and Firefox, including a 360 px viewport.
- Verification/automation: pytest and GitHub Actions per the repository baseline; load/performance and usability tools must be identified in the test plan where applicable.

### 2.5 Constraints

- The project is for one bank and the source baseline expressly excludes ATM functionality.
- Notifications are simulated and stored in the notification log; real SMS/e-mail gateway integration is outside the supplied scope.
- Requirement IDs supplied by the section authors are fixed and must not be renumbered during integration.
- Referenced business rules (BR-01 to BR-08) and design-specification identifiers (DS-*) must be resolved against the canonical baseline and SAD before the SRS is approved.

### 2.6 Assumptions and dependencies

- Teller and Admin actions are performed by authenticated users assigned the appropriate role.
- The ledger/transaction records are the source used to reconcile displayed balances and daily summaries.
- Customers can have more than one account only if the onboarding/account model supports it; account multiplicity rules are not fully described in the supplied parts and need confirmation.
- Minimum balance, daily withdrawal limit and other referenced business rules are defined by the shared rule baseline; their detailed text was not included in the supplied excerpts.
- The Test Plan and SAD are maintained separately under `docs/test-plan/` and `docs/sad/`; their requirement/test/module cross-references must be reconciled.

## 3. External Interface Requirements

### 3.1 User interface

The system shall expose the supported functions through a simple browser-based HTML/CSS/JavaScript interface. The available functions shall depend on the authenticated role. The UI shall present clear rejection messages for invalid transactions and account-status restrictions, support the transaction-history and statement flows, and satisfy BMS-NF-006 browser and responsive-viewport targets.

### 3.2 Software interface

- The browser client communicates with the FastAPI backend through REST/JSON interfaces in accordance with the repository baseline.
- The backend accesses SQLite through SQLAlchemy. Database operations affecting a transfer must satisfy BMS-NF-003 atomicity.
- The system is intended to use pytest and GitHub Actions for automated verification/CI. Exact service/module contracts are controlled by the SAD.

### 3.3 Communication interface

Client-server communication shall use TLS 1.2 or higher as required by BMS-SR-001. Specific deployment endpoints, certificates and local-development exceptions are not specified in the supplied excerpts and should be defined in the SAD/test environment documentation without weakening the requirement.

## 4. System Features

### 4.1 Authentication and access control

> Integration note: the provided Member 4 RTM contains summaries for BMS-F-001 through BMS-F-004, but the three source excerpts did not include a full Section 4.1. The statements below are conservative draft expansions of those summaries and must be checked against the canonical Part A / baseline v1.2 before approval.

#### BMS-F-001 - Authenticate user and create session

**Requirement statement:** The system shall authenticate a registered Customer, Teller or Admin using valid credentials and establish an authenticated session for the user.

**Type / category:** Functional  
**Priority:** High  
**Source / stakeholder:** Customer, Teller, Admin  
**Acceptance criteria / test reference:** Valid credentials establish a session for the correct user; invalid credentials do not establish a session; protected functions reject requests without a valid session. Test: TC-Auth-01.  
**Dependencies / comments:** DS-AUTH. Drafted from the RTM summary; verify wording against the canonical requirement baseline. Review note: Full source wording was not included in the three pasted part documents.

#### BMS-F-002 - Lock user after three failed logins

**Requirement statement:** The system shall lock a user account after three consecutive failed login attempts.

**Type / category:** Functional  
**Priority:** High  
**Source / stakeholder:** Customer, Teller, Admin  
**Acceptance criteria / test reference:** The third consecutive failed attempt puts the account into a locked state; a subsequent login is denied while the account remains locked. Test: TC-Auth-02.  
**Dependencies / comments:** DS-AUTH. The authorized recovery/unlock process and lock duration are not stated in the supplied part documents and must be confirmed. Review note: Threshold of three attempts appears in the supplied RTM summary.

#### BMS-F-003 - Enforce role-based access

**Requirement statement:** The system shall enforce role-based access to system functions for Customer, Teller and Admin users on the server.

**Type / category:** Functional  
**Priority:** High  
**Source / stakeholder:** Customer, Teller, Admin  
**Acceptance criteria / test reference:** A request by a role that is not permitted to perform the action is denied by the server; UI hiding alone is not sufficient. Test: TC-RBAC-01.  
**Dependencies / comments:** DS-AUTH; related security requirement BMS-SR-004.

#### BMS-F-004 - Change password and force first-login change

**Requirement statement:** The system shall allow an authenticated user to change their password and shall require a Customer issued a temporary password to change it at first login before using other protected banking functions.

**Type / category:** Functional  
**Priority:** High  
**Source / stakeholder:** Customer, Teller, Admin  
**Acceptance criteria / test reference:** A user can complete the password-change flow; a Customer with a temporary password cannot access other protected functions until the first-login password change is completed. Test: TC-Auth-03.  
**Dependencies / comments:** DS-AUTH; BMS-F-010 creates the temporary Customer credential. Review note: Confirm the password policy and whether the first-login rule applies to other role types.


### 4.2 Account management

This feature group enables authorized Tellers to open accounts, update customer contact details and search customers; Admins can freeze, unfreeze or close accounts; Customers can view only their own account details and current balance.

#### BMS-F-010 - Open account and create first Customer login

**Requirement statement:** The system shall allow a Teller to open a Savings or Current account by capturing name, date of birth, address, phone, ID-proof number and an opening deposit that meets the minimum balance (BR-01), and shall create a Customer login with a system-generated temporary password for a customer who has none.

**Type / category:** Functional  
**Priority:** High  
**Source / stakeholder:** Bank Operations  
**Acceptance criteria / test reference:** A unique 10-digit account number is generated; account status is Active; the opening deposit is recorded as a transaction; a Customer login is created with username equal to customer ID and a temporary password shown once to the Teller; no new login is created for an existing customer. Test: TC-Acc-01.  
**Dependencies / comments:** BR-01, BR-06, BR-08; DS-ACC, DS-AUTH, DS-TXN, DS-DB. Temporary password must be changed at first login under BMS-F-004. Review note: F-011 also mentions e-mail updates, but F-010 does not list e-mail among opening fields; confirm whether it is optional or should be captured at onboarding.

#### BMS-F-011 - Update customer contact details

**Requirement statement:** The system shall allow a Teller to update a customer's phone, e-mail and address and record the old and new values.

**Type / category:** Functional  
**Priority:** Medium  
**Source / stakeholder:** Bank Operations  
**Acceptance criteria / test reference:** Updated values are visible immediately; an audit entry holds the old and new values. Test: TC-Acc-02.  
**Dependencies / comments:** Audit recording; DS-ACC and DS-AUD.

#### BMS-F-012 - Freeze, unfreeze or close account

**Requirement statement:** The system shall allow an Admin to freeze, unfreeze or close an account; closure is permitted only when the balance is ₹0.

**Type / category:** Functional  
**Priority:** High  
**Source / stakeholder:** Bank Operations / Compliance  
**Acceptance criteria / test reference:** Frozen or closed accounts reject all transactions with a clear message; closure is rejected when the balance is not ₹0. Test: TC-Acc-03.  
**Dependencies / comments:** BR-04; DS-ACC and DS-TXN. Authorization must be enforced server-side.

#### BMS-F-013 - Customer views own accounts and balance

**Requirement statement:** The system shall allow a Customer to view details and current balance of only their own accounts.

**Type / category:** Functional  
**Priority:** High  
**Source / stakeholder:** Customer  
**Acceptance criteria / test reference:** Displayed balance equals the ledger sum; attempting to access another customer's account returns HTTP 403. Test: TC-Acc-04.  
**Dependencies / comments:** Server-side authorization under BMS-F-003 / BMS-SR-004; DS-ACC, DS-AUTH and DS-DB.

#### BMS-F-014 - Search customers

**Requirement statement:** The system shall allow a Teller to search customers by name, account number or phone and return results within 2 seconds.

**Type / category:** Functional  
**Priority:** Medium  
**Source / stakeholder:** Bank Operations  
**Acceptance criteria / test reference:** Partial-name search works; searches by account number and phone return matching customers; no match shows “No results”; response is within 2 seconds. Test: TC-Acc-05.  
**Dependencies / comments:** DS-ACC and DS-DB; displayed account numbers must follow BMS-SR-007 masking rules where applicable.


### 4.3 Transactions (deposit, withdrawal, transfer, history and statements)

The system shall record cash deposits and withdrawals, transfer funds between eligible BMS accounts, and provide transaction history and downloadable statements. All money movement is subject to referenced business rules; see Section 6 for rules that still require canonical definitions.

#### BMS-F-020 - Record cash deposit

**Requirement statement:** The system shall allow a Teller to record a cash deposit greater than ₹0 and less than or equal to ₹2,00,000 to an Active account and generate a receipt number.

**Type / category:** Functional  
**Priority:** High  
**Source / stakeholder:** Bank Operations / Customer  
**Acceptance criteria / test reference:** The balance increases by the exact deposited amount and a transaction record is created. Test: TC-Dep-01.  
**Dependencies / comments:** BMS-F-010; business rules BR-03 and BR-04.

#### BMS-F-021 - Record withdrawal within balance and daily limit

**Requirement statement:** The system shall allow a Teller to record a withdrawal only if the post-withdrawal balance is greater than or equal to the minimum balance and the daily limit (BR-02) is not exceeded.

**Type / category:** Functional  
**Priority:** High  
**Source / stakeholder:** Bank Operations / Customer  
**Acceptance criteria / test reference:** A valid withdrawal reduces the balance; an invalid withdrawal is rejected with a reason. Tests: TC-WD-01 and TC-WD-02.  
**Dependencies / comments:** Business rules BR-01, BR-02 and BR-05.

#### BMS-F-022 - Transfer funds between BMS accounts

**Requirement statement:** The system shall allow a Customer to transfer up to ₹1,00,000 per transfer from their account to another Active BMS account, rejecting transfers with insufficient funds or frozen/closed accounts.

**Type / category:** Functional  
**Priority:** High  
**Source / stakeholder:** Customer / Business  
**Acceptance criteria / test reference:** The debit and credit both succeed or both fail; two transaction records are created. Tests: TC-TR-01 and TC-TR-02.  
**Dependencies / comments:** Business rules BR-03, BR-04 and BR-05; related to BMS-NF-003.

#### BMS-F-023 - View transaction history and mini-statement

**Requirement statement:** The system shall allow a Customer to view their account transaction history filtered by date range, with the latest 10 transactions shown as a mini-statement.

**Type / category:** Functional  
**Priority:** Medium  
**Source / stakeholder:** Customer  
**Acceptance criteria / test reference:** Only transactions within the selected range are shown, newest first. Test: TC-Stmt-01.  
**Dependencies / comments:** Depends on BMS-F-020, BMS-F-021 and BMS-F-022.

#### BMS-F-024 - Download account statement

**Requirement statement:** The system shall allow a Customer to download a statement in CSV or PDF format for a chosen date range.

**Type / category:** Functional  
**Priority:** Low  
**Source / stakeholder:** Customer / Compliance  
**Acceptance criteria / test reference:** Totals in the downloaded file match the on-screen history. Test: TC-Stmt-02.  
**Dependencies / comments:** Depends on BMS-F-023.


### 4.4 Admin, audit, reporting and notification

This feature group provides authorized administration of Teller accounts, account-status changes, audit-log review, daily transaction reporting and simulated notification logging. Staff-management and account-status operations are restricted to Admin users. Notifications are written to a local log and are not sent through a real external SMS/e-mail gateway.

#### BMS-F-030 - Manage Teller user accounts

**Requirement statement:** The system shall allow an Admin to create, deactivate and unlock Teller user accounts.

**Type / category:** Functional  
**Priority:** High  
**Source / stakeholder:** Bank Operations  
**Acceptance criteria / test reference:** A new Teller can log in; a deactivated Teller cannot log in; an unlocked Teller can log in again. Test: TC-Adm-01.  
**Dependencies / comments:** DS-ADM and Auth Service integration.

#### BMS-F-031 - View filtered audit log

**Requirement statement:** The system shall allow an Admin to view the audit log filtered by user, action type and date.

**Type / category:** Functional  
**Priority:** Medium  
**Source / stakeholder:** Bank Operations / Compliance  
**Acceptance criteria / test reference:** The filter returns only matching entries. Test: TC-Aud-01.  
**Dependencies / comments:** Audit entries are produced under BMS-SR-006.

#### BMS-F-032 - Generate daily transaction summary

**Requirement statement:** The system shall generate a daily transaction summary for Admin showing the count and total of deposits, withdrawals and transfers.

**Type / category:** Functional  
**Priority:** Medium  
**Source / stakeholder:** Bank Operations  
**Acceptance criteria / test reference:** Report totals match the transaction table for the selected day. Test: TC-Rep-01.  
**Dependencies / comments:** Uses transaction records for the selected day.

#### BMS-F-033 - Log simulated transaction notification

**Requirement statement:** The system shall create a simulated e-mail/SMS notification record for the Customer after every debit or credit.

**Type / category:** Functional  
**Priority:** Low  
**Source / stakeholder:** Customer / Bank Operations  
**Acceptance criteria / test reference:** One notification record is created per credited or debited account. Test: TC-Not-01.  
**Dependencies / comments:** No real SMS/e-mail gateway is in scope; the Customer is the recipient.


## 5. Non-functional and security requirements

The quality requirements below are targets to be verified. Their inclusion is not a claim that the targets have already been achieved.

#### BMS-NF-001 - Transaction response time

**Requirement statement:** At least 95% of deposit, withdrawal and transfer requests shall complete within 3 seconds with 50 concurrent users.

**Type / category:** Performance  
**Priority:** High  
**Source / stakeholder:** Bank Operations / Customer  
**Acceptance criteria / test reference:** A load-test run with 50 concurrent users demonstrates a 95th-percentile response time no greater than 3 seconds. Test: TC-Perf-01.  
**Dependencies / comments:** DS-TXN; load-test tool/configuration to be specified in the Test Plan.

#### BMS-NF-002 - Availability and health endpoint

**Requirement statement:** The system shall be available 99.5% of each month, excluding scheduled maintenance, and expose a /health endpoint.

**Type / category:** Reliability  
**Priority:** Medium  
**Source / stakeholder:** Bank Operations  
**Acceptance criteria / test reference:** /health returns HTTP 200 within 1 second; availability is verified from an uptime log. Test: TC-Ops-01.  
**Dependencies / comments:** DS-UI / platform; the measurement window and uptime source should be confirmed in the Test Plan.

#### BMS-NF-003 - Atomic financial transactions

**Requirement statement:** Every financial transaction shall be atomic (ACID): a failed transfer leaves both account balances unchanged.

**Type / category:** Data integrity  
**Priority:** High  
**Source / stakeholder:** Customer / Bank Operations  
**Acceptance criteria / test reference:** A fault-injection test shows no partial transfer update: either both sides commit or neither does. Test: TC-TR-02.  
**Dependencies / comments:** DS-TXN, DS-DB. Review note: Storage-side trace: DS-DB.

#### BMS-NF-004 - First-time-user transfer usability

**Requirement statement:** At least 90% of first-time users shall complete a fund transfer within 2 minutes without help.

**Type / category:** Usability  
**Priority:** Medium  
**Source / stakeholder:** Customer  
**Acceptance criteria / test reference:** A usability study with at least 5 first-time users records the time and whether help was required. Test: TC-UX-01.  
**Dependencies / comments:** DS-UI. Confirm a sample-size/pass-count rule that meaningfully verifies the 90% target.

#### BMS-NF-005 - Audit log integrity and retention

**Requirement statement:** Audit logs shall be timestamped, append-only and retained for at least 5 years.

**Type / category:** Audit / retention  
**Priority:** Medium  
**Source / stakeholder:** Bank Operations / Compliance  
**Acceptance criteria / test reference:** There is no ordinary application update/delete path for audit logs; retention configuration is verified. Test: TC-Aud-02.  
**Dependencies / comments:** DS-AUD.

#### BMS-NF-006 - Browser compatibility and responsive UI

**Requirement statement:** The UI shall work on the latest two versions of Chrome, Edge and Firefox and be usable at a viewport width of 360 px.

**Type / category:** Compatibility  
**Priority:** Medium  
**Source / stakeholder:** Customer / Teller / Admin  
**Acceptance criteria / test reference:** Manual checks pass on the specified browser versions and a 360 px responsive viewport. Test: TC-UX-02.  
**Dependencies / comments:** DS-UI. The exact browser versions should be recorded when tests are performed.


### 5.1 Security objectives

| Objective ID | Objective | Description |
|---|---|---|
| BMS-SO-1 | Confidentiality | Customer and credential data shall be visible only to authorized users. Sensitive identifiers and authentication secrets shall be protected against unauthorized disclosure. |
| BMS-SO-2 | Integrity | Money movements and account data shall not be altered illegitimately or left in an inconsistent state. Validation, role enforcement and atomic transaction handling shall support this objective. |
| BMS-SO-3 | Accountability | Every security-relevant action shall be traceable to a user through timestamped audit records that identify the action and outcome. |

### 5.2 Security requirements

#### BMS-SR-001 - Require TLS for client-server communication

**Requirement statement:** The system shall use TLS 1.2 or higher for all client-server communication.

**Type / category:** Security  
**Priority:** High  
**Source / stakeholder:** Customer / Teller / Admin  
**Acceptance criteria / test reference:** Verification confirms that TLS 1.2 or higher is required for client-server communication. Test: TC-Sec-01.  
**Security objective link:** BMS-SO-1  
**Dependencies / comments:** DS-SEC.

#### BMS-SR-002 - Protect stored passwords

**Requirement statement:** The system shall store passwords, including temporary passwords, only as salted bcrypt or Argon2 hashes and shall never write them to logs.

**Type / category:** Security  
**Priority:** High  
**Source / stakeholder:** Customer / Teller / Admin  
**Acceptance criteria / test reference:** Stored password values are salted bcrypt/Argon2 hashes and password values are absent from logs. Test: TC-Sec-02.  
**Security objective link:** BMS-SO-1  
**Dependencies / comments:** DS-AUTH. A temporary password shown once to a Teller must not be written to logs or retained in recoverable form.

#### BMS-SR-003 - Expire idle sessions

**Requirement statement:** The system shall expire a session after 10 minutes of inactivity.

**Type / category:** Security  
**Priority:** Medium  
**Source / stakeholder:** Customer / Teller / Admin  
**Acceptance criteria / test reference:** A request after 10 minutes of inactivity is rejected and requires authentication. Test: TC-Sec-03.  
**Security objective link:** BMS-SO-1  
**Dependencies / comments:** DS-AUTH.

#### BMS-SR-004 - Enforce server-side authorization

**Requirement statement:** The system shall enforce authorization by role on the server for every request.

**Type / category:** Security  
**Priority:** High  
**Source / stakeholder:** Customer / Teller / Admin  
**Acceptance criteria / test reference:** A request by a role that is not eligible to perform the requested action is denied by the server. Test: TC-RBAC-01.  
**Security objective link:** BMS-SO-1, BMS-SO-2  
**Dependencies / comments:** DS-AUTH.

#### BMS-SR-005 - Validate input and mitigate SQL injection and XSS

**Requirement statement:** The system shall validate input on the server, use parameterized database queries to mitigate SQL injection, and apply context-appropriate output encoding to prevent cross-site scripting (XSS).

**Type / category:** Security  
**Priority:** High  
**Source / stakeholder:** Customer / Teller / Admin  
**Acceptance criteria / test reference:** SQL-injection inputs are safely handled by parameterized queries; XSS payloads are rendered inert or rejected by appropriate output encoding and validation. Test: TC-Sec-04.  
**Security objective link:** BMS-SO-2  
**Dependencies / comments:** DS-SEC. Editorial wording separates the SQL-injection control from the XSS control; confirm with the team before baseline approval. Review note: Corrected the causal wording in the source draft: parameterized queries alone do not prevent XSS.

#### BMS-SR-006 - Audit security-relevant actions

**Requirement statement:** The system shall record every login, financial and admin action in the audit log with user, timestamp, action and outcome.

**Type / category:** Security  
**Priority:** High  
**Source / stakeholder:** Bank Operations / Compliance  
**Acceptance criteria / test reference:** Required action records contain user, timestamp, action and outcome. Test: TC-Aud-01.  
**Security objective link:** BMS-SO-3  
**Dependencies / comments:** DS-AUD.

#### BMS-SR-007 - Mask account numbers and protect ID-proof numbers

**Requirement statement:** The system shall mask account numbers by showing only the last four digits in lists and logs, and encrypt ID-proof numbers at rest.

**Type / category:** Security  
**Priority:** Medium  
**Source / stakeholder:** Customer / Bank Operations / Compliance  
**Acceptance criteria / test reference:** Lists and logs show only the last four account-number digits; ID-proof numbers are encrypted at rest. Test: TC-Sec-05.  
**Security objective link:** BMS-SO-1  
**Dependencies / comments:** DS-SEC. The storage/encryption approach should be agreed with the SAD owner.


## 6. Business Rules and Constraints

The supplied requirements refer to BR-01 through BR-08, but their complete definitions were not present in the three pasted section excerpts. The following register records only what the supplied text establishes; it is deliberately not a substitute for the canonical rule definitions.

| Rule ID | Known from the supplied text | Missing / action required |
|---|---|---|
| BR-01 | Minimum-balance rule. Referenced for opening deposits and allowed post-withdrawal balance. | Exact minimum amount and account-type applicability are missing. |
| BR-02 | Daily withdrawal limit. | Numeric limit, time window and reset rule are missing. |
| BR-03 | Referenced by deposit and transfer requirements. | Rule text not supplied. |
| BR-04 | Referenced by account status and transaction requirements. | Rule text not supplied; confirm exact relationship to frozen/closed accounts. |
| BR-05 | Referenced by withdrawal and transfer requirements. | Rule text not supplied. |
| BR-06 | Referenced by account opening / Customer login creation. | Rule text not supplied. |
| BR-07 | No definition appears in the three supplied excerpts. | Locate in the canonical baseline or confirm that the identifier is obsolete. |
| BR-08 | Referenced by account opening / Customer login creation. | Rule text not supplied. |

**Other explicit limits currently recorded in functional requirements:** cash deposit > ₹0 and ≤ ₹2,00,000 (BMS-F-020); transfer ≤ ₹1,00,000 per transfer (BMS-F-022); account number is unique and 10 digits (BMS-F-010); lock after 3 consecutive failed logins (draft BMS-F-002); idle session timeout of 10 minutes (BMS-SR-003).

## 7. System Models and Diagrams

### 7.1 UML use-case diagram 2 - Admin and system

The diagram summarizes Admin Teller-management, account-status administration, audit-log review and daily reporting, together with the shared login use case and simulated notification logging. The PNG embedded in the DOCX is a clean reconstruction from the textual diagram description in the supplied Member 4 excerpt. Compare it with the canonical editable source and image under `docs/diagrams/` before final PR approval.

![Admin and system use-case diagram](../diagrams/usecase-2-admin.png)

*Figure 1. Admin and system use-case diagram. Notifications are logged locally; no external SMS/e-mail gateway is in scope.*

## 8. Requirements Traceability Matrix (RTM)

The RTM links each functional, non-functional and security requirement to an SRS section, design/module reference and planned test case. Status N is copied from the supplied Member 4 draft and means not started; it is not a test result. Confirm design-specification IDs and test identifiers against the current SAD and Test Plan before approval.

| Req ID | Requirement summary | Section / design ref | Module | Test case(s) | Status | Comments |
|---|---|---|---|---|---|
| BMS-F-001 | Authenticate user / create session | 4.1 / DS-AUTH | Auth Service | TC-Auth-01 | N | Drafted from RTM summary; verify canonical statement. |
| BMS-F-002 | Lock user after 3 failed logins | 4.1 / DS-AUTH | Auth Service | TC-Auth-02 | N | Lock-recovery flow not defined in supplied parts. |
| BMS-F-003 | Enforce role-based access | 4.1 / DS-AUTH | Auth Service | TC-RBAC-01 | N |  |
| BMS-F-004 | Change password / force first-login change | 4.1 / DS-AUTH | Auth Service | TC-Auth-03 | N | Drafted from RTM summary; verify canonical statement. |
| BMS-F-010 | Open account and create first Customer login | 4.2 / DS-ACC | Account Service | TC-Acc-01 | N |  |
| BMS-F-011 | Update customer contact details | 4.2 / DS-ACC | Account Service | TC-Acc-02 | N |  |
| BMS-F-012 | Freeze, unfreeze or close account | 4.2 / DS-ACC | Account Service | TC-Acc-03 | N |  |
| BMS-F-013 | Customer views own account and balance | 4.2 / DS-ACC | Account Service | TC-Acc-04 | N |  |
| BMS-F-014 | Teller searches customers | 4.2 / DS-ACC | Account Service | TC-Acc-05 | N |  |
| BMS-F-020 | Record cash deposit | 4.3 / DS-TXN | Transaction Service | TC-Dep-01 | N |  |
| BMS-F-021 | Record withdrawal within limits | 4.3 / DS-TXN | Transaction Service | TC-WD-01, TC-WD-02 | N |  |
| BMS-F-022 | Transfer funds between BMS accounts | 4.3 / DS-TXN | Transaction Service | TC-TR-01, TC-TR-02 | N |  |
| BMS-F-023 | View transaction history / mini-statement | 4.3 / DS-TXN | Transaction Service | TC-Stmt-01 | N |  |
| BMS-F-024 | Download CSV/PDF statement | 4.3 / DS-TXN | Transaction Service | TC-Stmt-02 | N |  |
| BMS-F-030 | Create, deactivate and unlock Teller users | 4.4 / DS-ADM | Admin & Reporting Service | TC-Adm-01 | N |  |
| BMS-F-031 | Admin filters and views audit log | 4.4 / DS-AUD | Audit & Notification Service | TC-Aud-01 | N |  |
| BMS-F-032 | Generate daily transaction summary | 4.4 / DS-ADM | Admin & Reporting Service | TC-Rep-01 | N |  |
| BMS-F-033 | Log simulated notification after every debit/credit | 4.4 / DS-AUD | Audit & Notification Service | TC-Not-01 | N |  |
| BMS-NF-001 | Transaction response time under 50-user load | 5 / DS-TXN | Transaction Service | TC-Perf-01 | N |  |
| BMS-NF-002 | 99.5% monthly availability and health endpoint | 5 / DS-UI | Web UI / Platform | TC-Ops-01 | N |  |
| BMS-NF-003 | Atomic financial transactions | 5 / DS-TXN, DS-DB | Transaction Service + Data Access Layer + Database | TC-TR-02 | N | Storage-side trace: DS-DB. |
| BMS-NF-004 | First-time-user transfer usability | 5 / DS-UI | Web UI / Platform | TC-UX-01 | N | Clarify sample-size/pass-count criteria. |
| BMS-NF-005 | Timestamped, append-only, 5-year audit retention | 5 / DS-AUD | Audit & Notification Service | TC-Aud-02 | N |  |
| BMS-NF-006 | Browser compatibility and 360 px responsive UI | 5 / DS-UI | Web UI / Platform | TC-UX-02 | N |  |
| BMS-SR-001 | TLS 1.2+ for client-server communication | 5.1 / DS-SEC | Security Layer | TC-Sec-01 | N |  |
| BMS-SR-002 | Salted password hashes; never log passwords | 5.1 / DS-AUTH | Auth Service | TC-Sec-02 | N |  |
| BMS-SR-003 | Expire session after 10 minutes idle | 5.1 / DS-AUTH | Auth Service | TC-Sec-03 | N |  |
| BMS-SR-004 | Server-side role authorization every request | 5.1 / DS-AUTH | Auth Service | TC-RBAC-01 | N |  |
| BMS-SR-005 | Validate input; protect against SQL injection and XSS | 5.1 / DS-SEC | Security Layer | TC-Sec-04 | N | Wording split between parameterized queries and output encoding. |
| BMS-SR-006 | Audit login, financial and admin actions | 5.1 / DS-AUD | Audit & Notification Service | TC-Aud-01 | N |  |
| BMS-SR-007 | Mask account numbers; encrypt ID-proof numbers | 5.1 / DS-SEC | Security Layer | TC-Sec-05 | N |  |

## 9. Integration Review Items

This draft is not approval-ready until the following items are resolved. Record decisions in the canonical baseline or the team review; do not silently invent missing thresholds or alter fixed identifiers.

### OI-01 - Business rules
Obtain the exact BR-01 to BR-08 definitions from the shared baseline. At minimum, confirm the minimum balance, withdrawal daily limit, transaction constraints, account onboarding and customer-login rules.

### OI-02 - Authentication Section 4.1
Confirm full, canonical statements and acceptance criteria for BMS-F-001 to BMS-F-004. The current section was expanded from the RTM summaries because no detailed Section 4.1 source was supplied.

### OI-03 - Requirement baseline/version
The account contribution refers to “shared baseline v1.2” while contribution documents and design/test docs are labelled v1.0. Confirm which version label applies to the requirements baseline versus this SRS document.

### OI-04 - Test-plan consistency
Verify every cited TC-* identifier exists in `docs/test-plan/Test_Plan_BankManagementSystem_v1.0.docx` and that its scenario and expected result match the SRS acceptance criteria. Remove or correct any orphan references.

### OI-05 - SAD/design references
Verify DS-AUTH, DS-ACC, DS-TXN, DS-DB, DS-AUD, DS-ADM, DS-SEC and DS-UI against the current SAD. Update references only after the SAD owner confirms the official names.

### OI-06 - Canonical diagram
Replace or compare the reconstructed figure in Section 7.1 against `docs/diagrams/usecase-2-admin.png` and its editable `.puml` source. Also confirm whether a use-case diagram 1 is required elsewhere in the SRS.

### OI-07 - Customer e-mail field
BMS-F-011 permits changing e-mail but BMS-F-010 does not capture e-mail during account opening. Confirm whether e-mail is optional/collected later or should be part of the onboarding fields.

### OI-08 - Temporary-password handling
Confirm how the one-time temporary password is displayed to the Teller without logging or storing it in recoverable form, consistent with BMS-SR-002. Confirm password policy details if they are part of the baseline.

### OI-09 - Lockout recovery
BMS-F-002 specifies three failed attempts, but the recovery actor, unlock mechanism and lock duration are not specified in the excerpts. Confirm the behavior for Customer, Teller and Admin accounts.

### OI-10 - Security wording
BMS-SR-005 in the source said parameterized queries prevent SQL injection and XSS. This draft separates database parameterization (SQL injection) from context-appropriate output encoding (XSS) while preserving the ID; approve this technical clarification.

### OI-11 - Usability test threshold
BMS-NF-004 requires at least 90% success and a study with at least five users. Define a sample-size/pass-count rule that makes the 90% threshold objectively verifiable.

### OI-12 - Business scope consistency
Keep ATM functionality out of scope. Preserve the no-real-SMS/e-mail-gateway scope and verify roles and account-status permissions across SRS, SAD, Test Plan and backlog.

### Approval

Prepared for team review by Member 1 (SRS owner and integration). Approval remains pending until the open items in this section are resolved and the integrated SRS is reviewed in a pull request.
