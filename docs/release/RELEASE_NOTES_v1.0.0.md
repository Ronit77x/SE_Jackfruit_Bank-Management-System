# Release Notes — Bank Management System (BMS) v1.0.0

- **Verified submission baseline:** `754d03c6d86927e490438ff7286c76f8258a2a12` (no tag creation is claimed)
- **Planned baseline date:** 30 October 2026 (planned date; not a release confirmation)
- **Team:** BMS_PES
- **Status:** Team-agreed submission baseline; application scope frozen on 17 November 2026. This documentation PR publishes the final verification record.

## 1. Scope

The project is a single-bank web-based Bank Management System with Customer, Teller and Admin roles. The documented scope includes authentication and role-based access, account management, deposits, withdrawals, internal fund transfers, transaction history/statements, audit logging and operational reporting.

## 2. Documentation baseline

- SRS v1.0: `docs/srs/`
- SAD v1.0: `docs/sad/`
- Test Plan v1.0: `docs/test-plan/`
- UML diagrams: `docs/diagrams/`
- Backlog and sprint planning: `docs/backlog/`
- Complete deviations and delivery-status log: [docs/deviations.md](../deviations.md)

The SRS consolidation note records 31 requirements (18 functional, 6 non-functional and 7 security), 8 business rules, 3 security objectives, 30 distinct referenced test cases and 8 design IDs. Ronit confirmed team agreement on the documented submission baseline on 17 November 2026.

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

See the [final verification record](FINAL_VERIFICATION_2026-11-17.md) for the complete regression result, exact verified commit and passing main CI. Historical counts are not the final baseline result.

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
- Final integrated verification: completed for the recorded application baseline; see the verification record.
- Team agreement: confirmed by Ronit on 17 November 2026; application scope frozen.

## 7. Release decision

The team has agreed on the submission baseline and its documented limitations,
as confirmed by Ronit on 17 November 2026. Both demo artifacts are present and
final verification is recorded. This agreement does not waive unmet SRS criteria.
The application scope is frozen at the verified commit; subsequent changes in
this PR only finalize documentation. After this PR merges and main CI passes,
issue #36 may be closed as Completed. No Git tag or GitHub Release is claimed.
