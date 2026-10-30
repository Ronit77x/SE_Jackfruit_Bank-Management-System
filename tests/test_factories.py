
from decimal import Decimal

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
