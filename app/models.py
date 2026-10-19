"""Database tables (SAD section 3.6). Owner: Member 3 (Ronit), story US-16.

If you need a new column or table: post it in the group chat, make an ADDITIVE change
(never rename or delete existing columns) in a small PR, and everyone pulls.
"""
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import ACCOUNT_ACTIVE, USER_ACTIVE
from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # customer ID (also the login username)
    name: Mapped[str] = mapped_column(String(120))
    date_of_birth: Mapped[date] = mapped_column(Date)
    address: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str] = mapped_column(String(20))
    email: Mapped[str] = mapped_column(String(120))
    id_proof_number: Mapped[str] = mapped_column(String(255))  # BMS-SR-007: must be encrypted at rest (US-05)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    accounts: Mapped[list["Account"]] = relationship(back_populates="customer")


class User(Base):
    """Login identity for Customers, Tellers and Admins (BMS-F-001..F-004, BMS-F-030)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))  # never store or log plain passwords (BMS-SR-002)
    role: Mapped[str] = mapped_column(String(20))  # Customer / Teller / Admin
    status: Mapped[str] = mapped_column(String(20), default=USER_ACTIVE)  # Active / Locked / Inactive
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_number: Mapped[str] = mapped_column(String(10), unique=True, index=True)  # BR-06: unique, 10 digits
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    type: Mapped[str] = mapped_column(String(20))  # Savings / Current
    balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(20), default=ACCOUNT_ACTIVE)  # Active / Frozen / Closed
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    customer: Mapped[Customer] = relationship(back_populates="accounts")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="account")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    type: Mapped[str] = mapped_column(String(20))  # see app/constants.py TXN_*
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    balance_after: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    receipt_no: Mapped[str | None] = mapped_column(String(40), unique=True, nullable=True)
    reference: Mapped[str | None] = mapped_column(String(60), nullable=True)  # links the two legs of a transfer
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)

    account: Mapped[Account] = relationship(back_populates="transactions")


class AuditLog(Base):
    """Append-only: never update or delete rows (BMS-NF-005, BMS-SR-006)."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(60), index=True)
    outcome: Mapped[str] = mapped_column(String(20))  # SUCCESS / FAILURE / DENIED
    details: Mapped[str] = mapped_column(Text, default="")  # never put passwords or full account numbers here


class Notification(Base):
    """Simulated e-mail/SMS record (BMS-F-033)."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="LOGGED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
