"""Money movement rules: BMS-F-020 deposit, BMS-F-021 withdrawal, BMS-F-022 transfer, BMS-NF-003 atomicity.

Owner: Member 3 (Ronit). Every function changes balances and writes its transaction rows in ONE
database transaction: it either commits completely or rolls back completely.
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import constants as c
from app.errors import AppError
from app.models import Account, Transaction
from app.services.audit_service import log_event


def mask_account_number(number: str) -> str:
    """Show only the last four digits (BMS-SR-007)."""
    return "*" * max(len(number) - 4, 0) + number[-4:]


def _get_account(db: Session, account_number: str) -> Account:
    account = db.scalar(select(Account).where(Account.account_number == account_number))
    if account is None:
        raise AppError(404, "ACCOUNT_NOT_FOUND", "Account not found.")
    return account


def _require_active(account: Account) -> None:
    if account.status != c.ACCOUNT_ACTIVE:
        raise AppError(409, "ACCOUNT_NOT_ACTIVE", "Account is frozen or closed.")


def _new_receipt() -> str:
    return "RCP-" + uuid.uuid4().hex[:12].upper()


def _record(db: Session, account: Account, txn_type: str, amount: Decimal, reference=None, receipt=None) -> Transaction:
    txn = Transaction(
        account_id=account.id,
        type=txn_type,
        amount=amount,
        balance_after=account.balance,
        receipt_no=receipt,
        reference=reference,
    )
    db.add(txn)
    db.flush()
    return txn


def deposit(db: Session, account_number: str, amount: Decimal, user_id: int | None) -> Transaction:
    """BMS-F-020: amount > 0 and <= DEPOSIT_LIMIT, account must be Active."""
    try:
        if amount <= 0 or amount > c.DEPOSIT_LIMIT:
            raise AppError(
                400, "INVALID_AMOUNT", f"Deposit must be greater than 0 and at most {c.DEPOSIT_LIMIT}."
            )
        account = _get_account(db, account_number)
        _require_active(account)
        account.balance = account.balance + amount
        txn = _record(db, account, c.TXN_DEPOSIT, amount, receipt=_new_receipt())
        db.commit()
    except AppError as exc:
        db.rollback()
        log_event(db, user_id, "DEPOSIT", "FAILURE", f"{mask_account_number(account_number)}: {exc.code}")
        raise
    except Exception:
        db.rollback()
        raise
    log_event(db, user_id, "DEPOSIT", "SUCCESS", f"{mask_account_number(account_number)} amount {amount}")
    return txn


def _withdrawn_today(db: Session, account_id: int) -> Decimal:
    start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    total = db.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.account_id == account_id,
            Transaction.type == c.TXN_WITHDRAWAL,
            Transaction.created_at >= start_of_day,
        )
    )
    return Decimal(str(total))


def withdraw(db: Session, account_number: str, amount: Decimal, user_id: int | None) -> Transaction:
    """BMS-F-021: balance after withdrawal must stay >= minimum balance; daily limit applies."""
    try:
        if amount <= 0:
            raise AppError(400, "INVALID_AMOUNT", "Amount must be greater than 0.")
        account = _get_account(db, account_number)
        _require_active(account)
        minimum = c.MIN_BALANCE[account.type]
        if account.balance - amount < minimum:
            raise AppError(
                422,
                "INSUFFICIENT_FUNDS",
                f"Balance after withdrawal would fall below the minimum balance of {minimum}.",
            )
        if _withdrawn_today(db, account.id) + amount > c.DAILY_WITHDRAWAL_LIMIT:
            raise AppError(
                422, "DAILY_LIMIT_EXCEEDED", f"Daily withdrawal limit of {c.DAILY_WITHDRAWAL_LIMIT} exceeded."
            )
        account.balance = account.balance - amount
        txn = _record(db, account, c.TXN_WITHDRAWAL, amount, receipt=_new_receipt())
        db.commit()
    except AppError as exc:
        db.rollback()
        log_event(db, user_id, "WITHDRAWAL", "FAILURE", f"{mask_account_number(account_number)}: {exc.code}")
        raise
    except Exception:
        db.rollback()
        raise
    log_event(db, user_id, "WITHDRAWAL", "SUCCESS", f"{mask_account_number(account_number)} amount {amount}")
    return txn
