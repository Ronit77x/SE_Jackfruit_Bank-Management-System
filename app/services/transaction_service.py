"""Money movement rules: BMS-F-020 deposit, BMS-F-021 withdrawal, BMS-F-022 transfer, BMS-NF-003 atomicity.

Owner: Member 3 (Ronit). Every function changes balances and writes its transaction rows in ONE
database transaction: it either commits completely or rolls back completely.
"""
import functools
import threading
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import constants as c
from app.errors import AppError
from app.models import Account, AuditLog, Transaction
from app.services.audit_service import log_event


# All money movements run one at a time. Without this, two requests that arrive together can both read the
# same balance and both succeed (a "lost update"). One lock is enough while the app runs as a single process
# on SQLite. With several server processes or another database, use row locks instead (SELECT ... FOR UPDATE).
_money_lock = threading.Lock()


def _serialized(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with _money_lock:
            return func(*args, **kwargs)

    return wrapper


def _audit(db: Session, user_id: int | None, action: str, outcome: str, details: str) -> None:
    """Adds the audit row to the CURRENT database transaction (no commit here).

    It is committed together with the balance change, so a money movement is never saved without its
    audit record, and an audit record is never saved for a movement that was rolled back.
    If writing the audit row fails, the whole movement is rolled back (nothing changes, the API reports an error).
    """
    db.add(AuditLog(user_id=user_id, action=action, outcome=outcome, details=details))


def _audit_failure(db: Session, user_id: int | None, action: str, outcome: str, details: str) -> None:
    """Best-effort audit record for a REJECTED request (nothing was changed).

    Runs after the rollback in its own transaction. A problem while writing it must never hide the real
    error that is returned to the caller, so any exception here is swallowed.
    """
    try:
        log_event(db, user_id, action, outcome, details)
    except Exception:
        db.rollback()


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


@_serialized
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
        _audit(db, user_id, "DEPOSIT", "SUCCESS", f"{mask_account_number(account_number)} amount {amount}")
        db.commit()
    except AppError as exc:
        db.rollback()
        _audit_failure(db, user_id, "DEPOSIT", "FAILURE", f"{mask_account_number(account_number)}: {exc.code}")
        raise
    except Exception:
        db.rollback()
        raise
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


@_serialized
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
        _audit(db, user_id, "WITHDRAWAL", "SUCCESS", f"{mask_account_number(account_number)} amount {amount}")
        db.commit()
    except AppError as exc:
        db.rollback()
        _audit_failure(db, user_id, "WITHDRAWAL", "FAILURE", f"{mask_account_number(account_number)}: {exc.code}")
        raise
    except Exception:
        db.rollback()
        raise
    return txn


def _credit(account: Account, amount: Decimal) -> None:
    account.balance = account.balance + amount


@_serialized
def transfer(
    db: Session,
    from_number: str,
    to_number: str,
    amount: Decimal,
    user_id: int | None,
    owner_customer_id: int | None = None,
    enforce_owner: bool = False,
) -> Transaction:
    """BMS-F-022 / BMS-NF-003: debit and credit succeed together or not at all.

    Returns the debit-side transaction. Both rows share one `reference`.
    """
    try:
        if from_number == to_number:
            raise AppError(400, "INVALID_TRANSFER", "Source and destination accounts must be different.")
        if amount <= 0:
            raise AppError(400, "INVALID_AMOUNT", "Amount must be greater than 0.")
        if amount > c.TRANSFER_LIMIT:
            raise AppError(
                422, "TRANSFER_LIMIT_EXCEEDED", f"Transfer limit of {c.TRANSFER_LIMIT} exceeded."
            )
        source = _get_account(db, from_number)
        destination = _get_account(db, to_number)
        if enforce_owner and source.customer_id != owner_customer_id:
            raise AppError(403, "FORBIDDEN", "You can only transfer from your own accounts.")
        _require_active(source)
        _require_active(destination)
        minimum = c.MIN_BALANCE[source.type]
        if source.balance - amount < minimum:
            raise AppError(
                422,
                "INSUFFICIENT_FUNDS",
                f"Balance after transfer would fall below the minimum balance of {minimum}.",
            )

        reference = "TRF-" + uuid.uuid4().hex[:12].upper()
        source.balance = source.balance - amount
        debit = _record(db, source, c.TXN_TRANSFER_OUT, amount, reference=reference)
        _credit(destination, amount)
        _record(db, destination, c.TXN_TRANSFER_IN, amount, reference=reference)
        _audit(
            db,
            user_id,
            "TRANSFER",
            "SUCCESS",
            f"{mask_account_number(from_number)} -> {mask_account_number(to_number)} amount {amount} ref {reference}",
        )
        db.commit()
    except AppError as exc:
        db.rollback()
        _audit_failure(
            db,
            user_id,
            "TRANSFER",
            "DENIED" if exc.status_code == 403 else "FAILURE",
            f"{mask_account_number(from_number)} -> {mask_account_number(to_number)}: {exc.code}",
        )
        raise
    except Exception:
        db.rollback()
        raise
    return debit
