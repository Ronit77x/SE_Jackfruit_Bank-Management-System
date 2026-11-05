"""Database engine and session handling. Owner: Member 3 (Ronit), story US-16.

The database location can be changed with the BMS_DATABASE_URL environment variable.
Default: a local SQLite file called bms.db (ignored by git).
"""
import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("BMS_DATABASE_URL", "sqlite:///./bms.db")

IS_SQLITE = DATABASE_URL.startswith("sqlite")

if IS_SQLITE:
    # check_same_thread: FastAPI runs each request in a worker thread.
    # timeout: wait up to 30 s for another writer instead of failing at once with "database is locked".
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False, "timeout": 30},
        # Every request holds one connection for its whole duration, and up to 40 requests run at the same time.
        # The default pool (5 + 10) ran out under 50 simultaneous users (500 errors found by the load test).
        pool_size=50,
        max_overflow=50,
    )

    @event.listens_for(engine, "connect")
    def _sqlite_settings(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")  # readers no longer block the writer
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()
else:
    engine = create_engine(DATABASE_URL, pool_size=20, max_overflow=40)

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
