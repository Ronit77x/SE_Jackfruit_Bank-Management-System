"""Simple data-access helpers (US-16). Owner: Member 3 (Ronit).

Other members may call these instead of writing their own queries, for example
`crud.create_customer`, `crud.get_account_by_number` and `crud.next_account_number`.
"""
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import ACCOUNT_ACTIVE, USER_ACTIVE
from app.models import Account, Customer, Notification, Transaction, User

FIRST_ACCOUNT_NUMBER = 1000000001


# ---------- customers ----------
def create_customer(db: Session, **fields) -> Customer:
    customer = Customer(**fields)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def get_customer(db: Session, customer_id: int) -> Customer | None:
    return db.get(Customer, customer_id)


def update_customer(db: Session, customer_id: int, **fields) -> Customer | None:
    customer = db.get(Customer, customer_id)
    if customer is None:
        return None
    for key, value in fields.items():
        setattr(customer, key, value)
    db.commit()
    db.refresh(customer)
    return customer


# ---------- users ----------
def create_user(
    db: Session,
    username: str,
    password_hash: str,
    role: str,
    customer_id: int | None = None,
    must_change_password: bool = False,
) -> User:
    user = User(
        username=username,
        password_hash=password_hash,
        role=role,
        status=USER_ACTIVE,
        customer_id=customer_id,
        must_change_password=must_change_password,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username))


def update_user(db: Session, user_id: int, **fields) -> User | None:
    user = db.get(User, user_id)
    if user is None:
        return None
    for key, value in fields.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


# ---------- accounts ----------
def next_account_number(db: Session) -> str:
    """Next unique 10-digit account number (BR-06)."""
    numbers = db.scalars(select(Account.account_number)).all()
    highest = max((int(n) for n in numbers), default=FIRST_ACCOUNT_NUMBER - 1)
    return str(highest + 1).zfill(10)


def create_account(
    db: Session,
    customer_id: int,
    account_type: str,
    balance: Decimal = Decimal("0"),
    account_number: str | None = None,
) -> Account:
    account = Account(
        account_number=account_number or next_account_number(db),
        customer_id=customer_id,
        type=account_type,
        balance=balance,
        status=ACCOUNT_ACTIVE,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def get_account_by_number(db: Session, account_number: str) -> Account | None:
    return db.scalar(select(Account).where(Account.account_number == account_number))


def update_account_status(db: Session, account_number: str, status: str) -> Account | None:
    account = get_account_by_number(db, account_number)
    if account is None:
        return None
    account.status = status
    db.commit()
    db.refresh(account)
    return account


# ---------- transactions and notifications ----------
def list_transactions(db: Session, account_id: int) -> list[Transaction]:
    return list(
        db.scalars(
            select(Transaction)
            .where(Transaction.account_id == account_id)
            .order_by(Transaction.created_at.desc(), Transaction.id.desc())
        )
    )


def create_notification(db: Session, customer_id: int, message: str) -> Notification:
    notification = Notification(customer_id=customer_id, message=message)
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification
