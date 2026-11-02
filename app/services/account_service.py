
"""Business logic for opening bank accounts."""

import secrets
from decimal import Decimal

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
from app.models import Account, Customer, Transaction, User
from app.security import hash_password


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
) -> dict:
    """Open an account and create a customer login for a first account."""

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

            customer = Customer(
                name=name,
                date_of_birth=date_of_birth,
                address=address,
                phone=phone,
                email=email,
                id_proof_number=id_proof_number,
            )
            db.add(customer)
            db.flush()

        # Determine whether this is the customer's first account.
        is_first_account = (
            db.query(Account).filter_by(customer_id=customer.id).first() is None
        )

        # Generate a unique 10-digit account number.
        account_number = None
        for _ in range(20):
            candidate = str(secrets.randbelow(9_000_000_000) + 1_000_000_000)
            exists = (
                db.query(Account)
                .filter_by(account_number=candidate)
                .first()
            )
            if exists is None:
                account_number = candidate
                break

        if account_number is None:
            raise RuntimeError("Could not generate a unique account number.")

        account = Account(
            account_number=account_number,
            customer_id=customer.id,
            type=account_type,
            balance=deposit,
            status=ACCOUNT_ACTIVE,
        )
        db.add(account)
        db.flush()

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
