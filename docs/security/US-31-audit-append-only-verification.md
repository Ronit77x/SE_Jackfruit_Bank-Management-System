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

Commands and outcomes:

```text
python -m pytest tests/test_audit_triggers.py -q
RESULT: 5 passed

python -m pytest tests/test_audit_service.py -q
RESULT: pytest exit code 4; file does not exist on this main baseline

python -m pytest
RESULT: 80 passed

python -m pip check
RESULT: No broken requirements found

git diff --check
RESULT: passed
```

The tests verify insert, update rejection, delete rejection, rollback-preserved
rows, idempotent installation, startup integration and unaffected unrelated
tables. They do not empirically measure five years of elapsed retention or
external backup/disaster-recovery retention.
