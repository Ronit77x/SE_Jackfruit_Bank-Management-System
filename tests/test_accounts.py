
from datetime import date
from decimal import Decimal

from app.constants import (
    ACCOUNT_ACTIVE,
    TXN_OPENING_DEPOSIT,
    ROLE_CUSTOMER,
)
from app.models import Account, Customer, Transaction, User
from app.security import verify_password


def new_customer_payload(account_type="Savings", deposit="1000.00"):
    return {
        "account_type": account_type,
        "deposit": deposit,
        "name": "Test Customer",
        "date_of_birth": "2000-01-01",
        "address": "1 Test Street",
        "phone": "9999999999",
        "email": "test@example.com",
        "id_proof_number": "TEST-ID-001",
    }


def test_open_savings_account_creates_transaction_and_login(client, db):
    response = client.post(
        "/accounts",
        headers={"X-Test-Role": "Teller"},
        json=new_customer_payload(),
    )

    assert response.status_code == 201
    data = response.json()

    assert len(data["account_number"]) == 10
    assert data["account_number"].isdigit()
    assert data["status"] == ACCOUNT_ACTIVE
    assert Decimal(data["balance"]) == Decimal("1000.00")
    assert data["temporary_password"]

    customer = db.get(Customer, data["customer_id"])
    account = db.get(Account, data["account_id"])
    user = db.query(User).filter_by(customer_id=customer.id).one()
    transaction = (
        db.query(Transaction).filter_by(account_id=account.id).one()
    )

    assert account.customer_id == customer.id
    assert user.username == str(customer.id)
    assert user.role == ROLE_CUSTOMER
    assert user.must_change_password is True
    assert verify_password(data["temporary_password"], user.password_hash)
    assert transaction.type == TXN_OPENING_DEPOSIT
    assert transaction.amount == Decimal("1000.00")
    assert transaction.balance_after == Decimal("1000.00")


def test_savings_deposit_below_minimum_is_rejected(client, db):
    response = client.post(
        "/accounts",
        headers={"X-Test-Role": "Teller"},
        json=new_customer_payload(deposit="500.00"),
    )

    assert response.status_code == 400
    assert db.query(Customer).count() == 0
    assert db.query(Account).count() == 0
    assert db.query(User).count() == 0
    assert db.query(Transaction).count() == 0


def test_current_account_requires_minimum_deposit(client, db):
    response = client.post(
        "/accounts",
        headers={"X-Test-Role": "Teller"},
        json=new_customer_payload(
            account_type="Current", deposit="4999.00"
        ),
    )

    assert response.status_code == 400
    assert db.query(Customer).count() == 0
    assert db.query(Account).count() == 0


def test_second_account_does_not_create_another_login(client, db):
    first = client.post(
        "/accounts",
        headers={"X-Test-Role": "Teller"},
        json=new_customer_payload(),
    )
    assert first.status_code == 201

    customer_id = first.json()["customer_id"]
    original_user_count = db.query(User).count()

    second = client.post(
        "/accounts",
        headers={"X-Test-Role": "Teller"},
        json={
            "customer_id": customer_id,
            "account_type": "Current",
            "deposit": "5000.00",
        },
    )

    assert second.status_code == 201
    data = second.json()
    assert "temporary_password" not in data
    assert db.query(User).count() == original_user_count
    assert db.query(Account).filter_by(customer_id=customer_id).count() == 2

def test_current_account_accepts_exact_minimum_deposit(client):
    response = client.post(
        "/accounts",
        headers={"X-Test-Role": "Teller"},
        json=new_customer_payload(
            account_type="Current",
            deposit="5000.00",
        ),
    )

    assert response.status_code == 201
    assert Decimal(response.json()["balance"]) == Decimal("5000.00")


def test_two_new_accounts_have_different_account_numbers(client):
    first = client.post(
        "/accounts",
        headers={"X-Test-Role": "Teller"},
        json=new_customer_payload(),
    )
    second = client.post(
        "/accounts",
        headers={"X-Test-Role": "Teller"},
        json={
            **new_customer_payload(),
            "email": "second@example.com",
            "id_proof_number": "TEST-ID-002",
        },
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert (
        first.json()["account_number"]
        != second.json()["account_number"]
    )
