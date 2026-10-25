"""Simple data-access helpers (US-16). Owner: Member 3 (Ronit).

Other members may call these instead of writing their own queries, for example
`crud.create_customer`, `crud.get_account_by_number` and `crud.next_account_number`.

How database transactions work (details: docs/database-transactions.md):
- Every helper in this file commits immediately. Use them for single, independent changes.
- Anything that moves money (deposit, withdrawal, transfer) must NOT be built from several helpers.
  Use app.services.transaction_service: it changes balances, writes the transaction rows and the audit row
  in ONE database transaction, commits once, and rolls everything back if anything goes wrong.

Transactions and audit logs are append-only records (BMS-NF-005): they can be created and read, but there are
deliberately no update or delete helpers for them.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.constants import ACCOUNT_ACTIVE, NOTIFICATION_STATUSES, USER_ACTIVE
from app.models import Account, AuditLog, Customer, Notification, Transaction, User

FIRST_ACCOUNT_NUMBER = 1000000001
MAX_ACCOUNT_NUMBER_ATTEMPTS = 5


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
    """Creates an account. The database column `account_number` is UNIQUE (BR-06).

    If no number is given, the next free one is generated. When two requests pick the same number at the
    same moment, the database rejects the second one (IntegrityError); we then roll back, pick a fresh
    number and try again (up to MAX_ACCOUNT_NUMBER_ATTEMPTS times). A number given explicitly is never retried.
    """
    for attempt in range(1, MAX_ACCOUNT_NUMBER_ATTEMPTS + 1):
        account = Account(
            account_number=account_number or next_account_number(db),
            customer_id=customer_id,
            type=account_type,
            balance=balance,
            status=ACCOUNT_ACTIVE,
        )
        db.add(account)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            if account_number is not None or attempt == MAX_ACCOUNT_NUMBER_ATTEMPTS:
                raise
            continue
        db.refresh(account)
        return account
    raise RuntimeError("unreachable")  # pragma: no cover


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


# ---------- transactions (append-only: create and read only) ----------
def create_transaction(
    db: Session,
    account_id: int,
    txn_type: str,
    amount: Decimal,
    balance_after: Decimal,
    receipt_no: str | None = None,
    reference: str | None = None,
) -> Transaction:
    """Stores one ledger row. It does NOT change the account balance: use the transaction service for that."""
    txn = Transaction(
        account_id=account_id,
        type=txn_type,
        amount=amount,
        balance_after=balance_after,
        receipt_no=receipt_no,
        reference=reference,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


def get_transaction(db: Session, transaction_id: int) -> Transaction | None:
    return db.get(Transaction, transaction_id)


def list_transactions(db: Session, account_id: int) -> list[Transaction]:
    return list(
        db.scalars(
            select(Transaction)
            .where(Transaction.account_id == account_id)
            .order_by(Transaction.created_at.desc(), Transaction.id.desc())
        )
    )


# ---------- audit log (append-only: create and read only) ----------
def create_audit_log(
    db: Session, user_id: int | None, action: str, outcome: str, details: str = ""
) -> AuditLog:
    """Never pass passwords or full account numbers in `details`."""
    entry = AuditLog(user_id=user_id, action=action, outcome=outcome, details=details)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_audit_log(db: Session, audit_id: int) -> AuditLog | None:
    return db.get(AuditLog, audit_id)


def list_audit_logs(
    db: Session,
    user_id: int | None = None,
    action: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 100,
) -> list[AuditLog]:
    query = select(AuditLog)
    if user_id is not None:
        query = query.where(AuditLog.user_id == user_id)
    if action is not None:
        query = query.where(AuditLog.action == action)
    if date_from is not None:
        query = query.where(AuditLog.timestamp >= date_from)
    if date_to is not None:
        query = query.where(AuditLog.timestamp <= date_to)
    return list(db.scalars(query.order_by(AuditLog.timestamp.desc(), AuditLog.id.desc()).limit(limit)))


# ---------- notifications (simulated e-mail/SMS records) ----------
def create_notification(db: Session, customer_id: int, message: str) -> Notification:
    notification = Notification(customer_id=customer_id, message=message)
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def get_notification(db: Session, notification_id: int) -> Notification | None:
    return db.get(Notification, notification_id)


def list_notifications(db: Session, customer_id: int) -> list[Notification]:
    return list(
        db.scalars(
            select(Notification)
            .where(Notification.customer_id == customer_id)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
        )
    )


def update_notification_status(db: Session, notification_id: int, status: str) -> Notification | None:
    """Allowed values: see NOTIFICATION_STATUSES in app/constants.py (LOGGED, SENT, FAILED)."""
    if status not in NOTIFICATION_STATUSES:
        raise ValueError(f"Invalid notification status {status!r}; allowed: {', '.join(NOTIFICATION_STATUSES)}")
    notification = db.get(Notification, notification_id)
    if notification is None:
        return None
    notification.status = status
    db.commit()
    db.refresh(notification)
    return notification
