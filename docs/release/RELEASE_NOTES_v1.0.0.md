# Release Notes — Bank Management System (BMS) v1.0.0

**Release Tag:** `v1.0.0`  
**Baseline Date:** October 30, 2026  
**Engineering Team:** BMS_PES (Ronit Prasad, Vijay Kumar, Tarini Arora, Vaibhava L)  
**Status:** Scope Freeze / Final Delivery Baseline  

---

## 1. Executive Summary

This release marks the final delivery and scope freeze of the Bank Management System (BMS). The system provides an end-to-end core banking solution with automated testing, continuous integration, layered service architecture, tamper-evident audit logging, and role-based access control.

---

## 2. Release Scope & Implemented Modules

### 2.1 Identity, Authentication & Access Control (M1 / M4)
- **BMS-F-001 (US-01):** User login with bearer token session tracking and 10-minute idle session timeout.
- **BMS-F-002 (US-02):** Automatic account lockout after 3 consecutive invalid authentication attempts; administrator unlock capability.
- **BMS-F-003 (US-03):** Role-based access control enforcing strict privilege boundaries across Customer, Teller, and Administrator roles.
- **BMS-F-004 (US-04):** Authenticated password change with password complexity enforcement (≥8 characters, uppercase, lowercase, digit) and mandatory first-login password replacement for temporary passwords.
- **BMS-SR-002 (US-05):** Bcrypt cryptographic password hashing with per-user salt and encrypted data protection at rest.

### 2.2 Customer & Account Lifecycle Management (M2)
- **BMS-F-010 (US-08):** Account opening for Savings and Current accounts with sequential 10-digit account number generation and minimum initial deposits (Savings: ₹1,000, Current: ₹5,000). Automated customer login creation upon first account.
- **BMS-F-011 (US-10):** Customer contact details updates (address, phone, email) with audit logging of previous and updated values.
- **BMS-F-012 (US-12):** Account state transitions across `Active`, `Frozen`, and `Closed` states, preventing debits/credits on frozen accounts and enforcing zero-balance closure.
- **BMS-F-013 (US-09):** Real-time account and balance inquiries with ownership validation.
- **BMS-F-014 (US-13):** Customer and account search by customer ID, account number, or name.

### 2.3 Financial Transaction Engine (M3)
- **BMS-F-020 (US-17):** Teller-assisted cash deposits with single transaction limit of ₹200,000 and receipt generation.
- **BMS-F-021 (US-18):** Teller-assisted cash withdrawals with daily limits of ₹50,000 and minimum balance protection.
- **BMS-F-022 (US-19):** Inter-account customer fund transfers with transaction limits, balance conservation, and atomic database rollback on failure.
- **BMS-F-023 (US-20, US-21):** Transaction history tracking, mini-statements, and statement exports.

### 2.4 Security, Governance & Operations (M4 / M1 / M2)
- **BMS-SR-006 (US-25, US-31):** Append-only audit logging recording security-critical events without plaintext credentials.
- **BMS-NF-002 (US-30):** Platform health check endpoint (`/health`) verifying service and database readiness.
- **US-06:** Automated continuous integration pipeline running full test suites on GitHub Actions runners.
- **US-11:** Reusable pytest fixtures and test data generation.

---

## 3. Database Schema Baseline

The relational schema managed under SQLAlchemy ORM includes:
- `customers`: Primary customer records and KYC references.
- `users`: User identity, password hashes, role, lockout counters, and password change flags.
- `accounts`: Bank account records, balances, types, and operational statuses.
- `transactions`: Double-entry transaction ledger with receipts and balance checkpoints.
- `audit_logs`: Append-only compliance log.
- `notifications`: Customer alert event log.

---

## 4. Test Execution Summary

The test suite covers functional, negative, concurrency, authorization, and audit requirements:
- **Pytest automated tests:** 100% passing across all core modules.
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

---

## 5. Known Limitations & Future Roadmap

1. **In-Memory Session Store:** Sessions are tracked in-memory; restarting the application server terminates existing bearer sessions. Persistent session storage (e.g., Redis) is planned for future iterations.
2. **Database Engine:** SQLite 3 is utilized as the baseline datastore. SQLite WAL mode and connection pooling optimize concurrent access; production migration to PostgreSQL is documented in the SAD.
3. **External Payment Gateways:** Fund transfers are supported internally within the bank; external inter-bank settlement integrations (IMPS/NEFT/RTGS) remain out of scope for this release.

---

## 6. Release Sign-Off

The project scope, requirements traceability, and codebase are frozen for evaluation and grading.
- **Baseline Git Tag:** `v1.0.0`
- **Signed off by:** Member 1, Member 2, Member 3, Member 4
