# How database transactions and rollback work

Applies to deposit (BMS-F-020), withdrawal (BMS-F-021) and fund transfer (BMS-F-022). Implemented in
`app/services/transaction_service.py`; related requirement: BMS-NF-003 (atomic financial transactions).

## One request = one database transaction

For every money movement the service does the following, in this order, inside a single database transaction:

1. **Check the rules** (amount limits, account status, minimum balance, daily limit, ownership). A rule violation raises `AppError`; nothing has been written yet.
2. **Change the balances** (one account for a deposit or withdrawal, two accounts for a transfer).
3. **Write the transaction rows** (`Transaction`): one for a deposit or withdrawal, two linked rows for a transfer.
4. **Write the audit row** (`AuditLog`) in the same transaction.
5. **Commit once.** Only now do all the changes become permanent, together.

## What happens when something goes wrong

| Situation | Result |
|---|---|
| A business rule is violated (for example insufficient funds, frozen account) | Rolled back, nothing changed. The caller gets a clear error (HTTP 4xx). A separate "FAILURE" audit row is written afterwards (best effort). |
| An unexpected error occurs at any step (for example the credit side of a transfer fails after the debit) | `db.rollback()` undoes every change of that request, including the debit. The error is raised to the caller (HTTP 500). Both balances stay as they were. |
| The audit row cannot be written | The whole movement is rolled back. We never save a money movement without its audit record. |
| Writing the "FAILURE" audit row for a rejected request fails | Ignored on purpose so the caller still gets the real error message. Nothing was changed anyway. |

Tests that prove this: `tests/test_transactions_transfer.py::test_failure_in_the_middle_rolls_back_both_sides`
and `tests/test_transactions_audit.py`.

## Simultaneous requests

Two requests that arrive at the same time could both read the same balance and both succeed (a "lost update"). To prevent this, `deposit`, `withdraw` and `transfer` run one at a time using a lock (`_money_lock`). This is enough while the application runs as a single process on SQLite. With several server processes or another database (for example PostgreSQL) the lock must be replaced by row locks (`SELECT ... FOR UPDATE`). Tests: `tests/test_transactions_concurrency.py`.

## The helpers in `app/crud.py`

Each helper commits immediately, so they are for single, independent changes. Never build a money movement out of several `crud` calls: a failure between two calls would leave half of it saved. Transactions and audit logs are append-only, so `crud` has create and read helpers for them but no update or delete.
