"""Reusable factories for test customers, users, and accounts."""

from datetime import date
from decimal import Decimal

from app.constants import (
    ACCOUNT_ACTIVE,
    ACCOUNT_SAVINGS,
    ROLE_CUSTOMER,
    USER_ACTIVE,
)
from app.models import Account, Customer, User
from app.security import hash_password


def create_customer(db, **overrides):
    """Create and return a sample customer in the test database."""
    data = {
        "name": "Test Customer",
        "date_of_birth": date(2000, 1, 1),
        "address": "1 Test Street",
        "phone": "9999999999",
        "email": "test@example.com",
        "id_proof_number": "TEST-ID-001",
    }
    data.update(overrides)

    customer = Customer(**data)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def create_user(db, customer=None, **overrides):
    """Create and return a sample customer login."""
    data = {
        "username": str(customer.id) if customer else "testuser",
        "password_hash": hash_password("TestPassword123!"),
        "role": ROLE_CUSTOMER,
        "status": USER_ACTIVE,
        "must_change_password": False,
        "customer_id": customer.id if customer else None,
    }
    data.update(overrides)

    user = User(**data)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_account(db, customer=None, **overrides):
    """Create and return a sample savings account."""
    if customer is None:
        customer = create_customer(db)

    data = {
        "account_number": "1000000001",
        "customer_id": customer.id,
        "type": ACCOUNT_SAVINGS,
        "balance": Decimal("1500.00"),
        "status": ACCOUNT_ACTIVE,
    }
    data.update(overrides)

    account = Account(**data)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account
