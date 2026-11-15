"""The production engine settings (app/database.py), checked on a real SQLite file and per backend."""
import sqlite3

import pytest
from sqlalchemy import text

from app.database import DEFAULT_MAX_OVERFLOW, DEFAULT_POOL_SIZE, build_engine, engine_options


def file_url(tmp_path):
    return f"sqlite:///{tmp_path / 'config.db'}"


def test_sqlite_uses_wal_and_waits_for_the_writer(tmp_path):
    engine = build_engine(file_url(tmp_path))
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA journal_mode")).scalar() == "wal"
        assert connection.execute(text("PRAGMA busy_timeout")).scalar() == 30000
    engine.dispose()


def test_pool_keeps_the_default_size_unless_it_is_changed_on_purpose(tmp_path, monkeypatch):
    monkeypatch.delenv("BMS_DB_POOL_SIZE", raising=False)
    monkeypatch.delenv("BMS_DB_MAX_OVERFLOW", raising=False)
    engine = build_engine(file_url(tmp_path))
    assert engine.pool.size() == DEFAULT_POOL_SIZE == 5
    assert engine.pool._max_overflow == DEFAULT_MAX_OVERFLOW == 10
    engine.dispose()


def test_pool_size_can_be_changed_with_environment_variables_for_experiments(monkeypatch):
    monkeypatch.setenv("BMS_DB_POOL_SIZE", "7")
    monkeypatch.setenv("BMS_DB_MAX_OVERFLOW", "3")
    options = engine_options("sqlite:///./x.db")
    assert options["pool_size"] == 7 and options["max_overflow"] == 3


def test_connection_health_options_are_for_client_server_databases_only():
    postgres = engine_options("postgresql://user:pw@localhost/bms")
    assert postgres["pool_pre_ping"] is True and postgres["pool_recycle"] == 1800
    sqlite = engine_options("sqlite:///./x.db")
    assert "pool_pre_ping" not in sqlite and "pool_recycle" not in sqlite
    assert "pool_size" not in engine_options("sqlite://")  # in-memory databases keep SQLAlchemy's own pool


@pytest.mark.parametrize("mode, writer_blocked", [("DELETE", True), ("WAL", False)])
def test_wal_lets_a_writer_commit_while_a_reader_is_open(tmp_path, mode, writer_blocked):
    """What WAL changes: in the old journal mode a writer cannot commit while any reader is open."""
    path = str(tmp_path / "wal.db")
    setup = sqlite3.connect(path)
    setup.execute(f"PRAGMA journal_mode={mode}")
    setup.execute("CREATE TABLE t (x INTEGER)")
    setup.execute("INSERT INTO t VALUES (1)")
    setup.commit()
    setup.close()

    reader = sqlite3.connect(path, timeout=0.3, isolation_level=None)
    reader.execute("BEGIN")
    reader.execute("SELECT * FROM t").fetchall()  # the reader stays inside its transaction
    writer = sqlite3.connect(path, timeout=0.3)
    try:
        writer.execute("INSERT INTO t VALUES (2)")
        writer.commit()
        blocked = False
    except sqlite3.OperationalError:
        blocked = True
    finally:
        reader.execute("ROLLBACK")
        reader.close()
        writer.close()
    assert blocked is writer_blocked
