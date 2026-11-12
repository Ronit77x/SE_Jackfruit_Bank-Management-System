"""Transaction endpoints. Owner: Member 3 (Ronit). Stories: US-17, US-18, US-19 (US-20, US-21 in Sprint 2).

An account is always identified by its 10-digit account number (string).
Money amounts are returned as strings such as "1500.00" so no precision is lost.
"""
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.constants import ROLE_CUSTOMER, ROLE_TELLER
from app.database import get_db
from app.deps import require_roles
from app.services import transaction_service as service

router = APIRouter(tags=["transactions"])

AccountNumber = Annotated[str, Field(pattern=r"^\d{10}$", description="10-digit account number")]
Amount = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]


class CashRequest(BaseModel):
    accountId: AccountNumber
    amount: Amount


class CashResponse(BaseModel):
    transactionId: int
    receiptNo: str | None
    balance: Decimal


@router.post("/transactions/deposit", response_model=CashResponse, status_code=201)
def deposit(body: CashRequest, user=Depends(require_roles(ROLE_TELLER)), db: Session = Depends(get_db)):
    """BMS-F-020. Teller records a cash deposit."""
    txn = service.deposit(db, body.accountId, body.amount, getattr(user, "id", None))
    return CashResponse(transactionId=txn.id, receiptNo=txn.receipt_no, balance=txn.balance_after)


@router.post("/transactions/withdraw", response_model=CashResponse, status_code=201)
def withdraw(body: CashRequest, user=Depends(require_roles(ROLE_TELLER)), db: Session = Depends(get_db)):
    """BMS-F-021. Teller records a withdrawal."""
    txn = service.withdraw(db, body.accountId, body.amount, getattr(user, "id", None))
    return CashResponse(transactionId=txn.id, receiptNo=txn.receipt_no, balance=txn.balance_after)


class TransferRequest(BaseModel):
    fromAccount: AccountNumber
    toAccount: AccountNumber
    amount: Amount


class TransferResponse(BaseModel):
    status: str
    transactionId: int
    reference: str | None
    balance: Decimal


@router.post("/transactions/transfer", response_model=TransferResponse, status_code=201)
def transfer(body: TransferRequest, user=Depends(require_roles(ROLE_CUSTOMER)), db: Session = Depends(get_db)):
    """BMS-F-022. Customer transfers money from one of their own accounts to another BMS account."""
    txn = service.transfer(
        db,
        body.fromAccount,
        body.toAccount,
        body.amount,
        getattr(user, "id", None),
        owner_customer_id=getattr(user, "customer_id", None),
        enforce_owner=getattr(user, "role", None) == ROLE_CUSTOMER,
    )
    return TransferResponse(status="SUCCESS", transactionId=txn.id, reference=txn.reference, balance=txn.balance_after)
