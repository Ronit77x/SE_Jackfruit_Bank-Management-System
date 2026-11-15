"""Database-level append-only protection for audit logs."""
from sqlalchemy.engine import Engine


def install_audit_triggers(engine: Engine) -> None:
    """Install SQLite triggers that reject updates and deletes of audit rows.

    SQLite is the supported database for this project. Raising for another
    dialect prevents callers from falsely assuming append-only protection was
    installed when these trigger definitions are not portable.
    """
    if engine.dialect.name != "sqlite":
        raise NotImplementedError("Audit append-only triggers are supported only for SQLite")

    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TRIGGER IF NOT EXISTS audit_logs_append_only_update
            BEFORE UPDATE ON audit_logs
            BEGIN
                SELECT RAISE(ABORT, 'audit_logs are append-only');
            END;
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TRIGGER IF NOT EXISTS audit_logs_append_only_delete
            BEFORE DELETE ON audit_logs
            BEGIN
                SELECT RAISE(ABORT, 'audit_logs are append-only');
            END;
            """
        )
