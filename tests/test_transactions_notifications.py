"""Simulated notification records for every debit and credit (BMS-F-033)."""
from decimal import Decimal

import pytest

from app import crud
from app.constants import ACCOUNT_FROZEN, ACCOUNT_SAVINGS, TXN_OPENING_DEPOSIT
from app.errors import AppError
from app.models import Notification
from app.services import transaction_service as service
from tests.test_crud import _customer


def account(db, balance="10000", customer=None):
    return crud.create_account(db, (customer or _customer(db)).id, ACCOUNT_SAVINGS, Decimal(balance))


def second_customer(db):
    return crud.create_customer(
        db, name="Other", date_of_birth=_customer.__globals__["date"](1999, 5, 5), address="b",
        phone="2", email="o@example.com", id_proof_number="other-id",
    )


def test_deposit_creates_one_notification_with_masked_account_and_new_balance(db):
    acct = account(db)
    service.deposit(db, acct.account_number, Decimal("500"), 1)
    notes = db.query(Notification).all()
    assert len(notes) == 1
    assert notes[0].customer_id == acct.customer_id and notes[0].status == "LOGGED"
    assert "Deposit of Rs 500.00" in notes[0].message and "Rs 10,500.00" in notes[0].message
    assert acct.account_number not in notes[0].message  # only the masked number
    assert acct.account_number[-4:] in notes[0].message


def test_withdrawal_creates_one_notification(db):
    acct = account(db)
    service.withdraw(db, acct.account_number, Decimal("2000"), 1)
    (note,) = db.query(Notification).all()
    assert "Withdrawal of Rs 2,000.00 from account" in note.message and "Rs 8,000.00" in note.message


def test_transfer_notifies_both_customers(db):
    source = account(db, "10000")
    destination = account(db, "2000", customer=second_customer(db))
    service.transfer(db, source.account_number, destination.account_number, Decimal("3000"), 1)
    notes = {n.customer_id: n.message for n in db.query(Notification).all()}
    assert set(notes) == {source.customer_id, destination.customer_id}
    assert "Transfer sent of Rs 3,000.00" in notes[source.customer_id] and "Rs 7,000.00" in notes[source.customer_id]
    assert "Transfer received of Rs 3,000.00" in notes[destination.customer_id]
    assert "Rs 5,000.00" in notes[destination.customer_id]


def test_rejected_requests_create_no_notification(db):
    acct = account(db, "1500")
    crud.update_account_status(db, acct.account_number, ACCOUNT_FROZEN)
    with pytest.raises(AppError):
        service.deposit(db, acct.account_number, Decimal("100"), 1)
    other = account(db, "1500")
    with pytest.raises(AppError):
        service.withdraw(db, other.account_number, Decimal("1000"), 1)  # below the minimum balance
    assert db.query(Notification).count() == 0


def test_failed_transfer_rolls_back_the_notifications_too(db, monkeypatch):
    source = account(db)
    destination = account(db, "2000")

    def broken_credit(acct, amount):
        raise RuntimeError("simulated failure after the debit")

    monkeypatch.setattr(service, "_credit", broken_credit)
    with pytest.raises(RuntimeError):
        service.transfer(db, source.account_number, destination.account_number, Decimal("3000"), 1)
    db.expire_all()
    assert db.query(Notification).count() == 0


def test_helper_supports_the_opening_deposit(db):
    acct = account(db, "1000")
    service.add_transaction_notification(db, acct, TXN_OPENING_DEPOSIT, Decimal("1000"))
    db.commit()
    (note,) = db.query(Notification).all()
    assert note.message.startswith("Opening deposit of Rs 1,000.00 to account")
