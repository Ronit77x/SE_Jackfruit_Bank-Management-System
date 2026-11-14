"""Database engine and session handling. Owner: Member 3 (Ronit), story US-16.

The database location can be changed with the BMS_DATABASE_URL environment variable.
Default: a local SQLite file called bms.db (ignored by git).

SQLite uses WAL so readers can coexist with a writer, with a 30-second busy
timeout and SQLAlchemy's default pool (5 + 10). Pool overrides support the
comparison in docs/database-pool-experiment.md. SQLite still has one writer;
larger pools do not remove that constraint.
"""
import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("BMS_DATABASE_URL", "sqlite:///./bms.db")

DEFAULT_POOL_SIZE = 5  # SQLAlchemy's own defaults
DEFAULT_MAX_OVERFLOW = 10


def _int_env(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def engine_options(url: str) -> dict:
    """Engine settings for the database behind `url`; chosen per backend, not applied blindly."""
    if url.startswith("sqlite"):
        options: dict = {
            # check_same_thread: requests run in worker threads.
            # timeout: wait up to 30 s for the single writer instead of failing at once with "database is locked".
            "connect_args": {"check_same_thread": False, "timeout": 30},
        }
        if ":memory:" not in url and url != "sqlite://":  # in-memory databases use their own single-connection pool
            options["pool_size"] = _int_env("BMS_DB_POOL_SIZE", DEFAULT_POOL_SIZE)
            options["max_overflow"] = _int_env("BMS_DB_MAX_OVERFLOW", DEFAULT_MAX_OVERFLOW)
        return options
    # Client/server databases (for example PostgreSQL): connections can be closed by the server or a firewall while
    # idle, so check them before use and replace old ones. Not needed for a local SQLite file.
    return {"pool_size": 20, "max_overflow": 10, "pool_pre_ping": True, "pool_recycle": 1800}


def build_engine(url: str, **overrides):
    engine = create_engine(url, **{**engine_options(url), **overrides})
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _sqlite_settings(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")  # readers no longer block the writer
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()

    return engine


engine = build_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: one database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
