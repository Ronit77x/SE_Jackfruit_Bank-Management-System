from decimal import Decimal

import pytest

from app import crud
from app.constants import ACCOUNT_CURRENT, ACCOUNT_FROZEN, ACCOUNT_SAVINGS
from app.models import AuditLog, Transaction
from tests.auth_helpers import act_as
from tests.test_crud import _customer


@pytest.fixture(autouse=True)
def logged_in_teller():
    """Deposits and withdrawals are Teller functions (BMS-F-020, BMS-F-021)."""
    act_as("Teller")


def make_account(db, balance="10000", account_type=ACCOUNT_SAVINGS, customer=None):
    customer = customer or _customer(db)
    return crud.create_account(db, customer.id, account_type, Decimal(balance))


def audit_actions(db):
    return [(row.action, row.outcome) for row in db.query(AuditLog).all()]


def test_deposit_increases_balance_and_creates_receipt(client, db):
    account = make_account(db, "10000")
    response = client.post("/transactions/deposit", json={"accountId": account.account_number, "amount": "5000"})
    assert response.status_code == 201
    body = response.json()
    assert Decimal(body["balance"]) == Decimal("15000.00")
    assert body["receiptNo"].startswith("RCP-")
    db.refresh(account)
    assert account.balance == Decimal("15000.00")
    assert db.query(Transaction).count() == 1
    assert ("DEPOSIT", "SUCCESS") in audit_actions(db)


def test_deposit_above_limit_is_rejected(client, db):
    account = make_account(db)
    response = client.post("/transactions/deposit", json={"accountId": account.account_number, "amount": "250000"})
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_AMOUNT"
    db.refresh(account)
    assert account.balance == Decimal("10000.00")


def test_deposit_zero_or_negative_is_rejected(client, db):
    account = make_account(db)
    for amount in ("0", "-5"):
        response = client.post("/transactions/deposit", json={"accountId": account.account_number, "amount": amount})
        assert response.status_code == 400
        assert response.json()["code"] == "VALIDATION_ERROR"


def test_deposit_to_frozen_account_is_rejected(client, db):
    account = make_account(db)
    crud.update_account_status(db, account.account_number, ACCOUNT_FROZEN)
    response = client.post("/transactions/deposit", json={"accountId": account.account_number, "amount": "100"})
    assert response.status_code == 409
    assert response.json()["code"] == "ACCOUNT_NOT_ACTIVE"
    assert ("DEPOSIT", "FAILURE") in audit_actions(db)


def test_deposit_unknown_account_returns_404(client):
    response = client.post("/transactions/deposit", json={"accountId": "9999999999", "amount": "100"})
    assert response.status_code == 404
    assert {"code", "message", "timestamp", "traceId"} <= set(response.json())
