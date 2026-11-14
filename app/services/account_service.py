"""Account and customer service logic. Owner: Member 2 (Vijay)."""

from typing import Any

from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import AuditLog, Customer


def update_customer_details(
    db: Session,
    customer_id: int,
    updates: dict[str, Any],
    teller_id: int | None,
) -> Customer:
    """Update contact details (phone, email, address) for an existing customer.

    Enforces business and audit rules (BMS-F-011, TC-Acc-02):
    1. Returns 404 AppError if the customer does not exist.
    2. Identifies real changes between old and new values.
    3. If no values changed, avoids unnecessary database writes and audit entries.
    4. If values changed, applies the updates and writes an audit log entry
       (action="CUSTOMER_UPDATE", outcome="SUCCESS") in the same database transaction.
    5. Completely rolls back changes if audit logging or commit fails.
    """
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise AppError(
            status_code=404,
            code="CUSTOMER_NOT_FOUND",
            message=f"Customer with ID {customer_id} not found.",
        )

    # Detect changed fields among allowed contact fields
    permitted_fields = ("phone", "email", "address")
    changes: dict[str, tuple[str, str]] = {}

    for field in permitted_fields:
        if field in updates and updates[field] is not None:
            new_val = updates[field]
            old_val = getattr(customer, field)
            if new_val != old_val:
                changes[field] = (old_val, new_val)

    # Avoid unnecessary DB writes and audit entries if nothing changed
    if not changes:
        return customer

    # Atomic update + audit log
    try:
        for field, (_, new_val) in changes.items():
            setattr(customer, field, new_val)

        diffs = [
            f"{field}: '{old}' -> '{new}'"
            for field, (old, new) in changes.items()
        ]
        audit_details = (
            f"Customer ID {customer_id} updated: " + "; ".join(diffs)
        )

        audit_entry = AuditLog(
            user_id=teller_id,
            action="CUSTOMER_UPDATE",
            outcome="SUCCESS",
            details=audit_details,
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(customer)
    except Exception:
        db.rollback()
        raise

    return customer
