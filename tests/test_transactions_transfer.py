from decimal import Decimal

from app import crud
from app.constants import ACCOUNT_CURRENT, ACCOUNT_FROZEN, ACCOUNT_SAVINGS
from app.models import AuditLog, Transaction
from tests.test_crud import _customer


def make_account(db, balance="10000", account_type=ACCOUNT_SAVINGS, customer=None):
    customer = customer or _customer(db)
    return crud.create_account(db, customer.id, account_type, Decimal(balance))


def audit_actions(db):
    return [(row.action, row.outcome) for row in db.query(AuditLog).all()]
from types import SimpleNamespace

import pytest

from app.deps import get_current_user
from app.main import app
from app.services import transaction_service


def as_customer(customer_id):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=1, username="c", role="Customer", customer_id=customer_id
    )


def test_transfer_moves_money_and_records_two_transactions(client, db):
    source = make_account(db, "10000")
    destination = make_account(db, "2000")
    as_customer(source.customer_id)
    response = client.post(
        "/transactions/transfer",
        json={"fromAccount": source.account_number, "toAccount": destination.account_number, "amount": "3000"},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "SUCCESS"
    db.refresh(source)
    db.refresh(destination)
    assert source.balance == Decimal("7000.00")
    assert destination.balance == Decimal("5000.00")
    rows = db.query(Transaction).all()
    assert len(rows) == 2
    assert rows[0].reference == rows[1].reference
    assert {row.type for row in rows} == {"TransferOut", "TransferIn"}
    assert ("TRANSFER", "SUCCESS") in audit_actions(db)


def test_transfer_with_insufficient_funds_changes_nothing(client, db):
    source = make_account(db, "1500")
    destination = make_account(db, "2000")
    as_customer(source.customer_id)
    response = client.post(
        "/transactions/transfer",
        json={"fromAccount": source.account_number, "toAccount": destination.account_number, "amount": "1000"},
    )
    assert response.status_code == 422
    db.refresh(source)
    db.refresh(destination)
    assert source.balance == Decimal("1500.00")
    assert destination.balance == Decimal("2000.00")
    assert db.query(Transaction).count() == 0


def test_transfer_above_limit_is_rejected(client, db):
    source = make_account(db, "500000")
    destination = make_account(db, "2000")
    as_customer(source.customer_id)
    response = client.post(
        "/transactions/transfer",
        json={"fromAccount": source.account_number, "toAccount": destination.account_number, "amount": "100000.01"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "TRANSFER_LIMIT_EXCEEDED"


def test_transfer_to_frozen_account_is_rejected(client, db):
    source = make_account(db, "10000")
    destination = make_account(db, "2000")
    crud.update_account_status(db, destination.account_number, ACCOUNT_FROZEN)
    as_customer(source.customer_id)
    response = client.post(
        "/transactions/transfer",
        json={"fromAccount": source.account_number, "toAccount": destination.account_number, "amount": "100"},
    )
    assert response.status_code == 409


def test_transfer_from_someone_elses_account_is_forbidden(client, db):
    source = make_account(db, "10000")
    destination = make_account(db, "2000")
    as_customer(customer_id=source.customer_id + 999)
    response = client.post(
        "/transactions/transfer",
        json={"fromAccount": source.account_number, "toAccount": destination.account_number, "amount": "100"},
    )
    assert response.status_code == 403
    db.refresh(source)
    assert source.balance == Decimal("10000.00")
    assert ("TRANSFER", "DENIED") in audit_actions(db)


def test_transfer_to_same_account_is_rejected(client, db):
    source = make_account(db, "10000")
    as_customer(source.customer_id)
    response = client.post(
        "/transactions/transfer",
        json={"fromAccount": source.account_number, "toAccount": source.account_number, "amount": "100"},
    )
    assert response.status_code == 400


def test_failure_in_the_middle_rolls_back_both_sides(db, monkeypatch):
    """BMS-NF-003 / TC-TR-02: a fault after the debit must leave BOTH balances unchanged."""
    source = make_account(db, "10000")
    destination = make_account(db, "2000")

    def broken_credit(account, amount):
        raise RuntimeError("simulated failure after the debit")

    monkeypatch.setattr(transaction_service, "_credit", broken_credit)
    with pytest.raises(RuntimeError):
        transaction_service.transfer(db, source.account_number, destination.account_number, Decimal("3000"), 1)

    db.expire_all()
    assert db.get(type(source), source.id).balance == Decimal("10000.00")
    assert db.get(type(destination), destination.id).balance == Decimal("2000.00")
    assert db.query(Transaction).count() == 0


def test_total_money_is_unchanged_by_a_transfer(client, db):
    source = make_account(db, "10000")
    destination = make_account(db, "2000")
    as_customer(source.customer_id)
    client.post(
        "/transactions/transfer",
        json={"fromAccount": source.account_number, "toAccount": destination.account_number, "amount": "2500"},
    )
    db.refresh(source)
    db.refresh(destination)
    assert source.balance + destination.balance == Decimal("12000.00")
