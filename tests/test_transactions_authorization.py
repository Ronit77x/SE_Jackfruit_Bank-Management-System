"""Authorization requirements for the transaction endpoints (BMS-F-003, BMS-SR-004).

The real login and role checks (US-01 / US-03, app/deps.py) enforce these rules.
"""
from types import SimpleNamespace

from app import crud
from app.constants import ACCOUNT_SAVINGS
from app.deps import get_current_user
from app.main import app
from tests.test_crud import _customer
from decimal import Decimal

def _account(db):
    return crud.create_account(db, _customer(db).id, ACCOUNT_SAVINGS, Decimal("10000"))


def _act_as(role, customer_id=None):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=7, username="u", role=role, customer_id=customer_id
    )


def test_customer_cannot_transfer_from_another_customers_account(client, db):
    """Ownership is enforced by the transaction service itself, independent of the login implementation."""
    source, destination = _account(db), _account(db)
    _act_as("Customer", customer_id=source.customer_id + 999)
    response = client.post(
        "/transactions/transfer",
        json={"fromAccount": source.account_number, "toAccount": destination.account_number, "amount": "100"},
    )
    assert response.status_code == 403


def test_customer_role_cannot_deposit(client, db):
    account = _account(db)
    _act_as("Customer", customer_id=account.customer_id)
    response = client.post("/transactions/deposit", json={"accountId": account.account_number, "amount": "100"})
    assert response.status_code == 403


def test_teller_role_cannot_transfer(client, db):
    source, destination = _account(db), _account(db)
    _act_as("Teller")
    response = client.post(
        "/transactions/transfer",
        json={"fromAccount": source.account_number, "toAccount": destination.account_number, "amount": "100"},
    )
    assert response.status_code == 403


def test_request_without_credentials_is_rejected(client, db):
    account = _account(db)
    response = client.post("/transactions/deposit", json={"accountId": account.account_number, "amount": "100"})
    assert response.status_code == 401
