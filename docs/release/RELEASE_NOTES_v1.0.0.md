# Release Notes — Bank Management System (BMS) v1.0.0 (Candidate Baseline - Part of #36)

- **Release Tag Candidate:** `v1.0.0-rc`
- **Planned Baseline Date:** October 30, 2026
- **Engineering Team:** BMS_PES (Ronit Prasad, Vijay Kumar, Tarini Arora, Vaibhava L)
- **Status:** Integration Baseline (Final Release Acceptance & Four-Member Sign-off Pending)

---

## 1. Executive Summary

This document captures the integration and documentation baseline of the Bank Management System (BMS). The system provides an end-to-end retail banking solution with automated testing, continuous integration, layered service architecture, database trigger-enforced audit logging, and role-based access control.

Formal release freeze, final verification sign-off, and final evaluation acceptance remain pending completion of all demo artifacts and member approvals (tracked as Part of #36).

---

## 2. Release Scope & Implemented Modules

### 2.1 Identity, Authentication & Access Control (M1 / M4)
- **BMS-F-001 (US-01):** User login with bearer token session tracking and 10-minute idle session timeout.
- **BMS-F-002 (US-02):** Automatic account lockout after 3 consecutive invalid authentication attempts; administrator unlock capability.
- **BMS-F-003 (US-03):** Role-based access control enforcing strict privilege boundaries across Customer, Teller, and Administrator roles.
- **BMS-F-004 (US-04):** Authenticated password change with password complexity enforcement (≥8 characters, uppercase, lowercase, digit, maximum 72 bytes) and mandatory first-login password replacement for temporary passwords.
- **BMS-SR-002 (US-05):** Bcrypt cryptographic password hashing with per-user salt and Fernet AES-128 encryption of sensitive KYC data (`id_proof_number`) at rest using `BMS_DATA_KEY`.

### 2.2 Customer & Account Lifecycle Management (M2)
- **BMS-F-010 (US-08):** Account opening for Savings and Current accounts with collision-resistant randomly generated 10-digit account numbers (BR-06) and minimum initial deposits (Savings: ₹1,000, Current: ₹5,000). Automated customer login creation upon first account and opening-deposit notification.
- **BMS-F-011 (US-10):** Customer contact details updates (address, phone, email) with audit logging of previous and updated values (`PUT /customers/{customer_id}`, Teller only).
- **BMS-F-012 (US-12):** Account state transitions across `Active`, `Frozen`, and `Closed` states, preventing debits/credits on frozen accounts, enforcing exact zero-balance closure, masking account numbers in audit logs, and atomic database commits.
- **BMS-F-013 (US-09):** Real-time account and balance inquiries with ownership validation (`GET /accounts`, customer role).
- **BMS-F-014 (US-13):** Customer and account search by full/partial customer name, normalized phone number (with separator stripping and country-code handling), or exact 10-digit account number (`GET /customers?q=...[&limit=...]`, Teller only) with account number masking (`******XXXX`).

### 2.3 Financial Transaction Engine (M3)
- **BMS-F-020 (US-17):** Teller-assisted cash deposits with single transaction limit of ₹200,000 and receipt generation.
- **BMS-F-021 (US-18):** Teller-assisted cash withdrawals with daily limits of ₹50,000 and minimum balance protection.
- **BMS-F-022 (US-19):** Inter-account customer fund transfers with transaction limits, balance conservation, dual customer notification, and atomic database rollback on failure.
- **BMS-F-023 (US-20):** Mini-statement returning the 10 most recent transactions for an account (`GET /accounts/{id}/statement/mini`).
- **BMS-F-024 (US-21):** Full transaction history statement download in CSV format (`GET /accounts/{id}/statement/download`) with date filtering, formula sanitization, and masked account numbers.

### 2.4 Security, Governance & Operations (M4 / M1 / M2)
- **BMS-SR-006 (US-25, US-31):** Append-only audit logging recording security-critical events without plaintext credentials. SQLite engine-level triggers abort UPDATE and DELETE operations, providing database-level table immutability against application mutations. *(Note: triggers provide relational immutability; they do not provide cryptographic hash chaining).*
- **BMS-NF-002 (US-30):** Platform health check endpoint (`/health`) verifying HTTP API service availability. *(Note: verifies process availability; does not execute database queries).*
- **US-06:** Automated continuous integration pipeline running full test suites on GitHub Actions runners.
- **US-11:** Reusable pytest fixtures and test data generation.

---

## 3. Database Schema Baseline (Source of Truth: `app/models.py`)

The relational schema managed under SQLAlchemy ORM includes:

1. **`customers`:** Primary customer records.
   - `id` (Integer, PK), `name` (String 120), `date_of_birth` (Date), `address` (String 255), `phone` (String 20), `email` (String 120), `id_proof_number` (String 255, Fernet-encrypted), `created_at` (DateTime).
2. **`users`:** Authentication principals.
   - `id` (Integer, PK), `username` (String 60, unique, indexed), `password_hash` (String 255), `role` (String 20), `status` (String 20), `failed_attempts` (Integer), `must_change_password` (Boolean), `customer_id` (ForeignKey `customers.id`, nullable), `created_at` (DateTime).
3. **`accounts`:** Bank accounts.
   - `id` (Integer, PK), `account_number` (String 10, unique, indexed), `customer_id` (ForeignKey `customers.id`), `type` (String 20), `balance` (Numeric 14,2), `status` (String 20), `opened_at` (DateTime).
4. **`transactions`:** Transaction ledger.
   - `id` (Integer, PK), `account_id` (ForeignKey `accounts.id`, indexed), `type` (String 20), `amount` (Numeric 14,2), `balance_after` (Numeric 14,2), `receipt_no` (String 40, unique, nullable), `reference` (String 60, nullable), `created_at` (DateTime, indexed).
5. **`audit_logs`:** Append-only compliance log.
   - `id` (Integer, PK), `timestamp` (DateTime, indexed), `user_id` (Integer, nullable), `action` (String 60, indexed), `outcome` (String 20), `details` (Text, masked account numbers).
6. **`notifications`:** Customer alert event log.
   - `id` (Integer, PK), `customer_id` (ForeignKey `customers.id`), `message` (Text), `status` (String 20), `created_at` (DateTime).

---

## 4. Test Execution Summary

The test suite covers functional, negative, concurrency, authorization, and audit requirements:
- **Pytest automated tests:** 100% passing across all core modules (310 tests passed).
- **Test execution commands:**
  ```bash
  pytest -v
  ```
- **Coverage Areas:**
  - Authentication, lockout concurrency, session expiration, password complexity.
  - Role-based route authorization.
  - Account opening, updates, status transitions, search.
  - Deposit, withdrawal, transfer balance integrity, daily limits.
  - Audit logging consistency and rollback protection.
  - Health check and uptime monitoring.

---

## 5. Known Limitations & Considerations

1. **In-Memory Session Store:** Sessions are tracked in-memory; restarting the application server terminates existing bearer sessions. Persistent session storage (e.g., Redis) is planned for future iterations.
2. **Database Engine:** SQLite 3 is utilized as the baseline datastore. SQLite WAL mode and connection pooling optimize concurrent access; production migration to PostgreSQL is documented in the SAD.
3. **External Payment Gateways:** Fund transfers are supported internally within the bank; external inter-bank settlement integrations (IMPS/NEFT/RTGS) remain simulated via internal transfers.
4. **Health Check Probing:** `/health` validates application process responsiveness; deep database probing is reserved for platform monitoring tools.

---

## 6. Release Sign-Off & Verification Status

- **Tracking Issue:** Part of #36
- **Sprint 1 Demo Video:** [docs/demo/sprint1-demo.mp4](docs/demo/sprint1-demo.mp4) (verified).
- **Sprint 2 Demo Recording:** Pending final video capture.
- **Deviations Document:** [docs/deviations.md](docs/deviations.md) maintained for evaluation.
- **Final Acceptance & Four-Member Sign-off:** **Pending** final team evaluation and formal sign-off.
