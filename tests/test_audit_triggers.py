import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, text
from sqlalchemy.exc import DatabaseError

from app.constants import AUDIT_RETENTION_YEARS
from app.models import AuditLog
from app.services.audit_triggers import install_audit_triggers


def _add_audit_record(db):
    record = AuditLog(user_id=1, action="TEST", outcome="SUCCESS", details="original")
    db.add(record)
    db.commit()
    return record


def test_installer_creates_expected_triggers_and_is_idempotent(db):
    engine = db.get_bind()

    install_audit_triggers(engine)
    install_audit_triggers(engine)

    names = {
        row[0]
        for row in db.execute(
            text("SELECT name FROM sqlite_master WHERE type = 'trigger' AND tbl_name = 'audit_logs'")
        )
    }
    assert names == {"audit_logs_append_only_update", "audit_logs_append_only_delete"}


def test_insert_update_delete_are_append_only(db):
    install_audit_triggers(db.get_bind())
    record = _add_audit_record(db)

    record.details = "changed"
    with pytest.raises(DatabaseError, match="append-only"):
        db.commit()
    db.rollback()
    assert db.get(AuditLog, record.id).details == "original"

    with pytest.raises(DatabaseError, match="append-only"):
        db.delete(record)
        db.commit()
    db.rollback()
    assert db.get(AuditLog, record.id) is not None


def test_unrelated_table_remains_mutable(db):
    metadata = MetaData()
    table = Table("unrelated", metadata, Column("id", Integer, primary_key=True), Column("value", String))
    metadata.create_all(db.get_bind())

    db.execute(table.insert().values(id=1, value="before"))
    db.commit()
    db.execute(table.update().where(table.c.id == 1).values(value="after"))
    db.commit()
    db.execute(table.delete().where(table.c.id == 1))
    db.commit()
    assert db.execute(table.select()).first() is None


def test_retention_policy_is_five_years():
    assert AUDIT_RETENTION_YEARS == 5


def test_app_startup_installs_triggers_on_isolated_engine(monkeypatch):
    from fastapi.testclient import TestClient

    import app.main as main_module
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool

    isolated_engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    monkeypatch.setattr(main_module, "engine", isolated_engine)

    with TestClient(main_module.app):
        trigger_names = {
            row[0]
            for row in isolated_engine.connect().execute(
                text("SELECT name FROM sqlite_master WHERE type = 'trigger' AND tbl_name = 'audit_logs'")
            )
        }

    assert trigger_names == {"audit_logs_append_only_update", "audit_logs_append_only_delete"}
