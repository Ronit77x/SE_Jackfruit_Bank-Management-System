"""Account numbers stay unique even when two requests pick the same number at the same time (BR-06)."""
import threading
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app import crud
from app.constants import ACCOUNT_SAVINGS
from app.database import Base
from tests.test_crud import _customer


def test_collision_is_retried_with_a_fresh_number(db, monkeypatch):
    customer = _customer(db)
    crud.create_account(db, customer.id, ACCOUNT_SAVINGS, Decimal("1000"))  # takes 1000000001

    numbers = iter(["1000000001", "1000000002"])  # first guess collides, second is free
    monkeypatch.setattr(crud, "next_account_number", lambda session: next(numbers))
    account = crud.create_account(db, customer.id, ACCOUNT_SAVINGS, Decimal("1000"))
    assert account.account_number == "1000000002"


def test_explicit_duplicate_number_is_rejected_not_retried(db):
    customer = _customer(db)
    crud.create_account(db, customer.id, ACCOUNT_SAVINGS, Decimal("1000"), account_number="1000000500")
    with pytest.raises(IntegrityError):
        crud.create_account(db, customer.id, ACCOUNT_SAVINGS, Decimal("1000"), account_number="1000000500")


def test_simultaneous_account_creation_gives_distinct_numbers(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'accounts.db'}", connect_args={"check_same_thread": False, "timeout": 10}
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with factory() as setup:
        customer_id = crud.create_customer(
            setup, name="C", date_of_birth=date(2000, 1, 1), address="a", phone="1", email="e", id_proof_number="i"
        ).id

    numbers, errors = [], []
    barrier = threading.Barrier(6)

    def worker():
        with factory() as session:
            barrier.wait()
            try:
                numbers.append(crud.create_account(session, customer_id, ACCOUNT_SAVINGS, Decimal("1000")).account_number)
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    engine.dispose()

    assert errors == []
    assert len(numbers) == 6 and len(set(numbers)) == 6
