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


def test_withdrawal_reduces_balance(client, db):
    account = make_account(db, "10000")
    response = client.post("/transactions/withdraw", json={"accountId": account.account_number, "amount": "2000"})
    assert response.status_code == 201
    assert Decimal(response.json()["balance"]) == Decimal("8000.00")
    assert ("WITHDRAWAL", "SUCCESS") in audit_actions(db)


def test_withdrawal_below_minimum_balance_is_rejected(client, db):
    account = make_account(db, "10000")  # Savings minimum is 1,000
    response = client.post("/transactions/withdraw", json={"accountId": account.account_number, "amount": "9500"})
    assert response.status_code == 422
    assert response.json()["code"] == "INSUFFICIENT_FUNDS"
    db.refresh(account)
    assert account.balance == Decimal("10000.00")


def test_current_account_has_higher_minimum_balance(client, db):
    account = make_account(db, "10000", ACCOUNT_CURRENT)  # Current minimum is 5,000
    response = client.post("/transactions/withdraw", json={"accountId": account.account_number, "amount": "6000"})
    assert response.status_code == 422
    ok = client.post("/transactions/withdraw", json={"accountId": account.account_number, "amount": "5000"})
    assert ok.status_code == 201


def test_daily_withdrawal_limit_is_enforced(client, db):
    account = make_account(db, "200000")
    first = client.post("/transactions/withdraw", json={"accountId": account.account_number, "amount": "40000"})
    assert first.status_code == 201
    second = client.post("/transactions/withdraw", json={"accountId": account.account_number, "amount": "20000"})
    assert second.status_code == 422
    assert second.json()["code"] == "DAILY_LIMIT_EXCEEDED"
    exactly = client.post("/transactions/withdraw", json={"accountId": account.account_number, "amount": "10000"})
    assert exactly.status_code == 201


def test_withdrawal_from_closed_account_is_rejected(client, db):
    account = make_account(db)
    crud.update_account_status(db, account.account_number, "Closed")
    response = client.post("/transactions/withdraw", json={"accountId": account.account_number, "amount": "100"})
    assert response.status_code == 409
