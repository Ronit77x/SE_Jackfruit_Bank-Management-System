"""Account service logic for customer account listing and details (US-14, BMS-NF-004).

Owner: Member 2 (Vijay).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Account


def mask_account_number(number: str | None) -> str:
    """Mask account number showing only the last 4 digits (BMS-SR-007).

    Valid 10-digit numbers return '******' + last 4 digits.
    Empty, None, or malformed values are handled safely.
    """
    if number is None:
        return ""
    clean = str(number).strip()
    if not clean:
        return ""
    if len(clean) == 10 and clean.isdigit():
        return "******" + clean[-4:]
    return "**********"


def get_customer_accounts(db: Session, customer_id: int) -> list[Account]:
    """Retrieve all bank accounts belonging to a given customer ID (BMS-NF-004)."""
    return list(
        db.scalars(
            select(Account)
            .where(Account.customer_id == customer_id)
            .order_by(Account.id.asc())
        ).all()
    )
