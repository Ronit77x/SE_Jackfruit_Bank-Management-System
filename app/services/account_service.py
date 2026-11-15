"""Business logic for account and customer operations.

Owner: Member 2 (Vijay). Stories: US-08, US-10.
"""

import secrets
from decimal import Decimal
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.constants import (
    ACCOUNT_ACTIVE,
    ACCOUNT_CURRENT,
    ACCOUNT_SAVINGS,
    MIN_BALANCE,
    ROLE_CUSTOMER,
    TXN_OPENING_DEPOSIT,
    USER_ACTIVE,
)
from app.errors import AppError
from app.models import Account, AuditLog, Customer, Transaction, User
from app.security import encrypt_value, hash_password


def open_account(
    db: Session,
    account_type: str,
    deposit: Decimal,
    customer_id: int | None = None,
    name: str | None = None,
    date_of_birth=None,
    address: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    id_proof_number: str | None = None,
    actor_id: int | None = None,
) -> dict:
    """Create a customer (if new), an account, an opening deposit and initial login.

    Rolls back all changes if any step fails.
    """
    if account_type not in (ACCOUNT_SAVINGS, ACCOUNT_CURRENT):
        raise ValueError("Account type must be Savings or Current.")

    if deposit < MIN_BALANCE[account_type]:
        raise ValueError(
            f"{account_type} accounts require an opening deposit of "
            f"at least ₹{MIN_BALANCE[account_type]}."
        )

    if deposit <= Decimal("0"):
        raise ValueError("Opening deposit must be positive.")

    try:
        if customer_id is not None:
            customer = db.get(Customer, customer_id)
            if customer is None:
                raise ValueError("Customer not found.")
        else:
            if not all(
                [name, date_of_birth, address, phone, email, id_proof_number]
            ):
                raise ValueError(
                    "All customer fields are required for a new customer."
                )

            encrypted_id = encrypt_value(id_proof_number)
            if len(encrypted_id) > 255:
                raise ValueError("ID proof is too long for encrypted storage.")

            customer = Customer(
                name=name,
                date_of_birth=date_of_birth,
                address=address,
                phone=phone,
                email=email,
                id_proof_number=encrypted_id,
            )
            db.add(customer)
            db.flush()

        # Determine whether this is the customer's first account.
        is_first_account = (
            db.query(Account).filter_by(customer_id=customer.id).first() is None
        )

        # sqlite3 legacy mode does not BEGIN for SELECT. A first SAVEPOINT would
        # otherwise commit an existing customer's account when released, so the
        # final rollback could not undo it. Ensure an outer transaction exists.
        if db.get_bind().dialect.name == "sqlite":
            connection = db.connection()
            if not connection.connection.driver_connection.in_transaction:
                connection.exec_driver_sql("BEGIN")

        # The UNIQUE constraint arbitrates collisions, including concurrent requests.
        # A savepoint rolls back only the attempted account, preserving the customer.
        account = None
        for _ in range(20):
            candidate = str(secrets.randbelow(9_000_000_000) + 1_000_000_000)
            try:
                with db.begin_nested():
                    proposed = Account(
                        account_number=candidate,
                        customer_id=customer.id,
                        type=account_type,
                        balance=deposit,
                        status=ACCOUNT_ACTIVE,
                    )
                    db.add(proposed)
                    db.flush()
                account = proposed
                break
            except IntegrityError:
                if db.query(Account).filter_by(account_number=candidate).first() is None:
                    raise
        if account is None:
            raise RuntimeError("Could not generate a unique account number.")

        transaction = Transaction(
            account_id=account.id,
            type=TXN_OPENING_DEPOSIT,
            amount=deposit,
            balance_after=deposit,
        )
        db.add(transaction)

        temporary_password = None

        if is_first_account:
            existing_login = (
                db.query(User).filter_by(customer_id=customer.id).first()
            )
            if existing_login is None:
                temporary_password = secrets.token_urlsafe(12)
                user = User(
                    username=str(customer.id),
                    password_hash=hash_password(temporary_password),
                    role=ROLE_CUSTOMER,
                    status=USER_ACTIVE,
                    must_change_password=True,
                    customer_id=customer.id,
                )
                db.add(user)

        # Do not call log_event here: its independent commit breaks atomicity.
        # These details contain no credentials, ID proof or account number.
        db.add(AuditLog(
            user_id=actor_id,
            action="ACCOUNT_OPENED",
            outcome="SUCCESS",
            details=f"Customer ID {customer.id}; account type {account.type}",
        ))
        db.commit()
        db.refresh(customer)
        db.refresh(account)
        db.refresh(transaction)

        return {
            "customer_id": customer.id,
            "account_id": account.id,
            "account_number": account.account_number,
            "account_type": account.type,
            "balance": str(account.balance),
            "status": account.status,
            "transaction_id": transaction.id,
            "temporary_password": temporary_password,
        }

    except Exception:
        db.rollback()
        raise


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
