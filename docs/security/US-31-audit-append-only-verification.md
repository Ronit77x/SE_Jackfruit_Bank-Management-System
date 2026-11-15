# US-31 audit append-only verification

## Policy and implementation

- `AUDIT_RETENTION_YEARS` is configured as `5` in `app/constants.py`.
- The application has no purge job. The constant is a policy configuration,
  not evidence that five years of history have elapsed.
- SQLite trigger `audit_logs_append_only_update` rejects every update to an
  existing `audit_logs` row with `audit_logs are append-only`.
- SQLite trigger `audit_logs_append_only_delete` rejects every delete from the
  `audit_logs` table with `audit_logs are append-only`.
- The triggers are installed after table creation during application startup.
- The installer is idempotent and does not recreate or modify the table.

## Verified tests

The following tests exercise actual database operations:

- `test_installer_creates_expected_triggers_and_is_idempotent`
- `test_insert_update_delete_are_append_only`
- `test_unrelated_table_remains_mutable`
- `test_retention_policy_is_five_years`
- `test_app_startup_installs_triggers_on_isolated_engine`

The audit-service tests in `tests/test_audit_service.py` verify that supported
outcomes are persisted, unsupported outcomes are rejected without creating a
row, password-like details and account numbers are redacted, ordinary details
and phone numbers are preserved, and the public `log_event` signature remains
compatible. The audit-trigger tests verify idempotent installation, successful
inserts, update/delete rejection, rollback preservation of the original row,
unaffected unrelated tables, the five-year policy constant and startup
installation on an isolated engine.

Commands and outcomes:

The exact focused and full-suite commands and results are recorded below after
the latest-main integration verification:

```text
python -m pytest tests/test_audit_triggers.py tests/test_audit_service.py -q
RESULT: 21 passed, 1 warning in 0.05s

python -m pytest -v
RESULT: 271 passed, 1 warning in 37.15s

python -m pip check
RESULT: No broken requirements found

python -m compileall -q app scripts
RESULT: passed

git diff --check
RESULT: passed
```

The tests verify insert, update rejection, delete rejection, rollback-preserved
rows, idempotent installation, startup integration and unaffected unrelated
tables. They do not empirically measure five years of elapsed retention or
external backup/disaster-recovery retention. The five-year value is a configured
retention policy only; backup and disaster-recovery retention remain unverified.
