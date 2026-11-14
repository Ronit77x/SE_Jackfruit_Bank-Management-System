from datetime import date
from decimal import Decimal

from app import crud
from app.constants import ACCOUNT_FROZEN, ACCOUNT_SAVINGS, ROLE_TELLER


def _customer(db):
    return crud.create_customer(
        db,
        name="Test Customer",
        date_of_birth=date(2000, 1, 1),
        address="1 Test Street",
        phone="9999999999",
        email="test@example.com",
        id_proof_number="ID123",
    )


def test_customer_create_read_update(db):
    customer = _customer(db)
    assert crud.get_customer(db, customer.id).name == "Test Customer"
    crud.update_customer(db, customer.id, phone="8888888888")
    assert crud.get_customer(db, customer.id).phone == "8888888888"
    assert crud.get_customer(db, 9999) is None


def test_user_create_read_update(db):
    user = crud.create_user(db, "teller1", "hash", ROLE_TELLER)
    assert crud.get_user_by_username(db, "teller1").id == user.id
    crud.update_user(db, user.id, failed_attempts=2)
    assert crud.get_user_by_username(db, "teller1").failed_attempts == 2


def test_account_numbers_are_unique_ten_digit_and_sequential(db):
    customer = _customer(db)
    first = crud.create_account(db, customer.id, ACCOUNT_SAVINGS, Decimal("1000"))
    second = crud.create_account(db, customer.id, ACCOUNT_SAVINGS, Decimal("1000"))
    assert first.account_number == "1000000001"
    assert second.account_number == "1000000002"
    assert len(first.account_number) == 10


def test_account_status_update_and_lookup(db):
    customer = _customer(db)
    account = crud.create_account(db, customer.id, ACCOUNT_SAVINGS, Decimal("1000"))
    crud.update_account_status(db, account.account_number, ACCOUNT_FROZEN)
    assert crud.get_account_by_number(db, account.account_number).status == ACCOUNT_FROZEN
    assert crud.get_account_by_number(db, "0000000000") is None
