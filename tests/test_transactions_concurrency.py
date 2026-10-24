"""Concurrent requests must never create or destroy money (BMS-NF-003).

These tests use a real SQLite file and separate database sessions, one per thread, like separate requests.
"""
import threading
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import crud
from app.database import Base
from app.errors import AppError
from app.models import Transaction
from app.services import transaction_service as service

ROUNDS = 25


@pytest.fixture()
def session_factory(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'race.db'}", connect_args={"check_same_thread": False, "timeout": 10}
    )
    Base.metadata.create_all(bind=engine)
    yield sessionmaker(bind=engine, autoflush=False, autocommit=False)
    engine.dispose()


def _new_account(factory, balance):
    with factory() as db:
        customer = crud.create_customer(
            db, name="C", date_of_birth=date(2000, 1, 1), address="a", phone="1", email="e", id_proof_number="i"
        )
        return crud.create_account(db, customer.id, "Savings", Decimal(balance)).account_number


def _run_together(factory, jobs):
    """Run each job in its own thread with its own session, all starting at the same moment."""
    barrier = threading.Barrier(len(jobs))
    outcomes = []

    def run(job):
        with factory() as db:
            barrier.wait()
            try:
                job(db)
                outcomes.append("ok")
            except AppError:
                outcomes.append("rejected")

    threads = [threading.Thread(target=run, args=(job,)) for job in jobs]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return outcomes


def test_two_simultaneous_withdrawals_cannot_both_succeed(session_factory):
    for _ in range(ROUNDS):
        number = _new_account(session_factory, "10000")  # minimum balance 1,000 -> only ONE 9,000 withdrawal fits
        outcomes = _run_together(
            session_factory,
            [lambda db: service.withdraw(db, number, Decimal("9000"), 1)] * 2,
        )
        assert sorted(outcomes) == ["ok", "rejected"]
        with session_factory() as db:
            assert crud.get_account_by_number(db, number).balance == Decimal("1000.00")
            assert db.query(Transaction).filter_by(type="Withdrawal").count() >= 1


def test_simultaneous_transfers_conserve_total_money(session_factory):
    for _ in range(ROUNDS):
        source = _new_account(session_factory, "10000")
        first = _new_account(session_factory, "2000")
        second = _new_account(session_factory, "2000")
        outcomes = _run_together(
            session_factory,
            [
                lambda db: service.transfer(db, source, first, Decimal("9000"), 1),
                lambda db: service.transfer(db, source, second, Decimal("9000"), 1),
            ],
        )
        assert sorted(outcomes) == ["ok", "rejected"]
        with session_factory() as db:
            total = sum(crud.get_account_by_number(db, n).balance for n in (source, first, second))
            assert total == Decimal("14000.00")
            assert crud.get_account_by_number(db, source).balance == Decimal("1000.00")


def test_simultaneous_deposits_are_all_counted(session_factory):
    number = _new_account(session_factory, "1000")
    outcomes = _run_together(
        session_factory,
        [lambda db: service.deposit(db, number, Decimal("100"), 1)] * 8,
    )
    assert outcomes == ["ok"] * 8
    with session_factory() as db:
        assert crud.get_account_by_number(db, number).balance == Decimal("1800.00")
