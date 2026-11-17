# Release Notes — Bank Management System (BMS) v1.0.0

- **Candidate tag:** `v1.0.0-rc`
- **Planned baseline date:** 30 October 2026 (planned date; not a release confirmation)
- **Team:** BMS_PES
- **Status:** Documentation/integration candidate. Final freeze and team acceptance are pending.

## 1. Scope

The project is a single-bank web-based Bank Management System with Customer, Teller and Admin roles. The documented scope includes authentication and role-based access, account management, deposits, withdrawals, internal fund transfers, transaction history/statements, audit logging and operational reporting.

## 2. Documentation baseline

- SRS v1.0: `docs/srs/`
- SAD v1.0: `docs/sad/`
- Test Plan v1.0: `docs/test-plan/`
- UML diagrams: `docs/diagrams/`
- Backlog and sprint planning: `docs/backlog/`
- Complete deviations and delivery-status log: [docs/deviations.md](../deviations.md)

The SRS consolidation note records 31 requirements (18 functional, 6 non-functional and 7 security), 8 business rules, 3 security objectives, 30 distinct referenced test cases and 8 design IDs. The SRS team approval is still pending.

## 3. Database schema

The authoritative SQLAlchemy models are in `app/models.py`. The six tables/models are:

1. `customers`
2. `users`
3. `accounts`
4. `transactions`
5. `audit_logs`
6. `notifications`

The transaction model fields are `id`, `account_id`, `type`, `amount`, `balance_after`, `receipt_no`, `reference` and `created_at`. The notification model fields are `id`, `customer_id`, `message`, `status` and `created_at`.

## 4. Security configuration and limitations

Sensitive KYC data is encrypted using Fernet. The key is read from the `BMS_DATA_KEY` environment variable. The application does not automatically load `.env` files. Never commit the key.

**For a fresh database:** Generate a new Fernet key once and set it in the environment before starting the application. Keep the key safe and reuse that same key whenever accessing data encrypted in this database.

Generate a fresh key using:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Set the generated key in the environment before starting the application.

Windows CMD:

```cmd
set BMS_DATA_KEY=YOUR_NEW_KEY
```

Linux/macOS:

```bash
export BMS_DATA_KEY="YOUR_NEW_KEY"
```

**For an existing database:** Do **not** generate a new key. Set the exact original `BMS_DATA_KEY` that was used to encrypt the database's KYC values.

Windows CMD:

```cmd
set BMS_DATA_KEY=YOUR_EXISTING_KEY
```

Linux/macOS:

```bash
export BMS_DATA_KEY="YOUR_EXISTING_KEY"
```

A different key cannot decrypt existing ciphertext. If the original key is lost, the encrypted values cannot be recovered from the database alone.

Passwords are hashed with bcrypt. The audit-log database triggers reject `UPDATE` and `DELETE` operations, providing append-only enforcement at the database table level; they do not provide cryptographic hash chaining or external tamper evidence.

The `/health` endpoint returns `{"status": "ok"}` and does not query the database. It therefore demonstrates process-level responsiveness, not database readiness.

## 5. Verification status

Run the complete suite from the final integrated checkout:

```bash
pytest -v
```

**Final integrated test count and CI result: pending verification.** Historical test counts from earlier branches are not presented as the final release result because subsequent changes have been integrated.

## 6. Known limitations and pending acceptance

- Active sessions are stored in application memory and are invalidated when the server restarts.
- Transfers are internal to the bank; external NEFT/RTGS/IMPS gateway integration is outside the implemented scope.
- `/health` does not perform a database connectivity check.
- Sprint 1 demo video: [Watch Sprint 1 demo](../demo/sprint1-demo.mp4).
- Sprint 2 demo video: [`docs/demo/sprint2-demo.mp4`](../demo/sprint2-demo.mp4), recorded by Vaibhava L. (Member 4), present in the repository. The measured duration is **270.90 seconds (4 minutes 31 seconds)**, exceeding the assignment's two-minute requirement; no assessor waiver is claimed.
- **Usability verification:** The minimum first-time-user usability sample was not met.
- **Browser coverage:** Cross-browser verification remains partial. Testing against the latest two versions of supported browsers has not been completed, and physical touchscreen testing remains incomplete.
- **Monthly availability:** Monthly availability requirements have not yet been demonstrated.
- The complete [deviations and delivery-status log](../deviations.md) documents Sprint 1 and Sprint 2 implementation choices, delivery deviations, and incomplete acceptance criteria.
- Final integrated verification: pending.
- Final release freeze and four-member acceptance/sign-off: pending.

## 7. Release decision

`v1.0.0-rc` is a candidate baseline only. Do not create or announce a final `v1.0.0` release until the integrated test suite and CI have been verified, the Sprint 2 demo and required evidence are present, the known limitations are reviewed, and all four team members approve the release.