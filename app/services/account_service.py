"""Account and customer service logic. Owner: Member 2 (Vijay)."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import ACCOUNT_ACTIVE, ACCOUNT_CLOSED, ACCOUNT_FROZEN
from app.errors import AppError
from app.models import Account, AuditLog
from app.services.transaction_service import _money_lock


def get_account_by_identifier(db: Session, identifier: str | int) -> Account | None:
    """Find an account by 10-digit account_number or primary key ID.

    If the identifier is a 10-digit numeric string, look up strictly by account_number.
    Do not fall back to primary-key lookup if that account number does not exist.
    If the identifier is a shorter numeric string (length < 10), look up by integer ID.
    Otherwise, look up by account_number.
    """
    ident_str = str(identifier).strip()

    # 10-digit numeric string is strictly an account number (no fallback to PK ID)
    if len(ident_str) == 10 and ident_str.isdigit():
        return db.scalar(select(Account).where(Account.account_number == ident_str))

    # Numeric identifiers with length != 10 are looked up by primary key ID
    if ident_str.isdigit():
        return db.get(Account, int(ident_str))

    # Non-digit identifiers fallback to account_number match
    return db.scalar(select(Account).where(Account.account_number == ident_str))


def update_account_status(
    db: Session,
    account_identifier: str | int,
    target_status: str,
    admin_id: int | None,
) -> Account:
    """Freeze, unfreeze, or close a bank account (BMS-F-012, TC-Acc-03).

    Synchronized via `_money_lock` to prevent racing with money movements.
    """
    with _money_lock:
        account = get_account_by_identifier(db, account_identifier)
        if account is None:
            raise AppError(
                status_code=404,
                code="ACCOUNT_NOT_FOUND",
                message=f"Account '{account_identifier}' not found.",
            )

        current_status = account.status
        normalized_target = target_status.strip().capitalize()

        # Closed accounts cannot be modified
        if current_status == ACCOUNT_CLOSED:
            raise AppError(
                status_code=400,
                code="ACCOUNT_ALREADY_CLOSED",
                message="A closed account cannot be reopened or have its status modified.",
            )

        # Reject repeated status transition
        if current_status == normalized_target:
            raise AppError(
                status_code=400,
                code="INVALID_STATUS_TRANSITION",
                message=f"Account is already in '{current_status}' status.",
            )

        # Validate specific transitions
        if normalized_target == ACCOUNT_FROZEN:
            if current_status != ACCOUNT_ACTIVE:
                raise AppError(
                    status_code=400,
                    code="INVALID_STATUS_TRANSITION",
                    message=f"Only an Active account can be frozen; current status is '{current_status}'.",
                )
            action_name = "ACCOUNT_FREEZE"

        elif normalized_target == ACCOUNT_ACTIVE:
            if current_status != ACCOUNT_FROZEN:
                raise AppError(
                    status_code=400,
                    code="INVALID_STATUS_TRANSITION",
                    message=f"Only a Frozen account can be unfrozen; current status is '{current_status}'.",
                )
            action_name = "ACCOUNT_UNFREEZE"

        elif normalized_target == ACCOUNT_CLOSED:
            # Closure requires balance to be exactly 0
            if account.balance != Decimal("0"):
                raise AppError(
                    status_code=400,
                    code="CANNOT_CLOSE_NONZERO_BALANCE",
                    message=(
                        f"An account can be closed only when its balance is exactly 0. "
                        f"Current balance is {account.balance}."
                    ),
                )
            action_name = "ACCOUNT_CLOSE"

        else:
            raise AppError(
                status_code=400,
                code="INVALID_STATUS",
                message=f"Invalid target status '{target_status}'. Must be Active, Frozen, or Closed.",
            )

        # Atomic status change + audit log
        try:
            account.status = normalized_target
            audit_details = (
                f"Account {account.account_number} (ID {account.id}) "
                f"status changed from {current_status} to {normalized_target}"
            )
            audit_entry = AuditLog(
                user_id=admin_id,
                action=action_name,
                outcome="SUCCESS",
                details=audit_details,
            )
            db.add(audit_entry)
            db.commit()
            db.refresh(account)
        except Exception:
            db.rollback()
            raise

        return account
