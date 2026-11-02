from decimal import Decimal

from app.constants import ROLE_CUSTOMER
from app.models import Account, Customer, User
from tests.factories import create_account, create_customer, create_user


def test_factories_create_customer_user_and_account(db):
    customer = create_customer(db)
    user = create_user(db, customer=customer)
    account = create_account(db, customer=customer)

    assert db.query(Customer).filter_by(id=customer.id).one() == customer
    assert db.query(User).filter_by(id=user.id).one() == user
    assert db.query(Account).filter_by(id=account.id).one() == account
    assert account.customer_id == customer.id
    assert account.balance == Decimal("1500.00")
    assert user.customer_id == customer.id


def test_create_user_default_links_customer(db):
    user = create_user(db)

    assert user.role == ROLE_CUSTOMER
    assert user.customer_id is not None
    assert db.query(Customer).filter_by(id=user.customer_id).one()


def test_repeated_create_user_generates_unique_usernames(db):
    first_user = create_user(db)
    second_user = create_user(db)

    assert first_user.username != second_user.username
    assert first_user.customer_id != second_user.customer_id


def test_repeated_create_account_generates_unique_10_digit_numbers(db):
    customer = create_customer(db)

    first_account = create_account(db, customer=customer)
    second_account = create_account(db, customer=customer)

    assert first_account.account_number != second_account.account_number
    assert len(first_account.account_number) == 10
    assert len(second_account.account_number) == 10
    assert first_account.account_number.isdigit()
    assert second_account.account_number.isdigit()


def test_factories_allow_explicit_username_and_account_number(db):
    customer = create_customer(db)

    user = create_user(
        db,
        customer=customer,
        username="custom_test_user",
    )
    account = create_account(
        db,
        customer=customer,
        account_number="1234567890",
    )

    assert user.username == "custom_test_user"
    assert account.account_number == "1234567890"