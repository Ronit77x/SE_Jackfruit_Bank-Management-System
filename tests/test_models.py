"""Smoke test: the tables exist and a record can be written and read back (US-16)."""
from decimal import Decimal

from app.models import Account, Customer


def test_create_and_read_account(db):
    from datetime import date

    customer = Customer(
        name="Test Customer",
        date_of_birth=date(2000, 1, 1),
        address="1 Test Street",
        phone="9999999999",
        email="test@example.com",
        id_proof_number="ID123",
    )
    db.add(customer)
    db.commit()
    db.add(Account(account_number="1000000001", customer_id=customer.id, type="Savings", balance=Decimal("1500.00")))
    db.commit()

    account = db.query(Account).filter_by(account_number="1000000001").one()
    assert account.balance == Decimal("1500.00")
    assert account.status == "Active"
