"""Transaction endpoints. Owner: Member 3 (Ronit). Stories: US-17, US-18, US-19 (US-20, US-21 in Sprint 2).

An account is always identified by its 10-digit account number (string).
Money amounts are returned as strings such as "1500.00" so no precision is lost.
"""
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.constants import ROLE_CUSTOMER, ROLE_TELLER
from app.database import get_db
from app.deps import require_roles
from app.services import transaction_service as service
from app.services.audit_service import log_event

router = APIRouter(tags=["transactions"])

AccountNumber = Annotated[str, Field(pattern=r"^[0-9]{10}$", description="10-digit ASCII account number")]
Amount = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]


class CashRequest(BaseModel):
    model_config = {"extra": "forbid"}
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
    model_config = {"extra": "forbid"}
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


# ---------------------------------------------------------------------------------------------------------------
# History (BMS-F-023) and statement download (BMS-F-024): Customer, own accounts only. Dates are India time.
# ---------------------------------------------------------------------------------------------------------------
PathAccount = Annotated[str, Path(pattern=r"^[0-9]{10}$", description="10-digit account number")]


class HistoryItem(BaseModel):
    transactionId: int
    type: str
    amount: Decimal
    balanceAfter: Decimal
    receiptNo: str | None
    reference: str | None
    createdAt: str


class HistoryResponse(BaseModel):
    account: str
    miniStatement: bool
    total: int          # all transactions in the range (or of the account for the mini-statement)
    count: int          # how many are in this response
    limit: int | None
    offset: int
    hasMore: bool       # true when more transactions exist beyond this page
    transactions: list[HistoryItem]


@router.get("/accounts/{account_number}/transactions", response_model=HistoryResponse)
def history(
    account_number: PathAccount,
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    limit: int = Query(default=service.DEFAULT_PAGE_SIZE, ge=1, le=service.MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    user=Depends(require_roles(ROLE_CUSTOMER)),
    db: Session = Depends(get_db),
):
    """Latest 10 transactions, or the transactions between `from` and `to` (YYYY-MM-DD, India time), page by page.

    A date range with more than `limit` transactions is returned in pages: `total` says how many there are and
    `hasMore` tells whether to ask for the next page with a larger `offset`. Nothing is dropped silently.
    """
    account, rows, mini, total = service.list_history(
        db, account_number, getattr(user, "customer_id", None), True, date_from, date_to, limit=limit, offset=offset
    )
    has_more = total > len(rows) if mini else offset + len(rows) < total
    return HistoryResponse(
        account=service.mask_account_number(account.account_number),
        miniStatement=mini,
        total=total,
        count=len(rows),
        limit=None if mini else limit,
        offset=0 if mini else offset,
        hasMore=has_more,
        transactions=[
            HistoryItem(
                transactionId=row.id,
                type=row.type,
                amount=row.amount,
                balanceAfter=row.balance_after,
                receiptNo=row.receipt_no,
                reference=row.reference,
                createdAt=service.to_bank_time(row.created_at).isoformat(),
            )
            for row in rows
        ],
    )


@router.get("/accounts/{account_number}/statement")
def statement(
    account_number: PathAccount,
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
    file_format: str = Query(default="csv", alias="format"),
    user=Depends(require_roles(ROLE_CUSTOMER)),
    db: Session = Depends(get_db),
):
    """Statement for a date range as a CSV file. Only format=csv is available."""
    if file_format.lower() != "csv":
        raise service.AppError(400, "UNSUPPORTED_FORMAT", "Only format=csv is available.")
    # limit=None: the statement contains EVERY transaction of the period, so its totals are always complete.
    account, rows, _, total = service.list_history(
        db, account_number, getattr(user, "customer_id", None), True, date_from, date_to, newest_first=False, limit=None
    )
    text, _, _ = service.build_statement_csv(account, rows, date_from, date_to)
    try:  # downloading a statement is recorded (BMS-SR-006); only the masked account number is written
        log_event(
            db,
            getattr(user, "id", None),
            "STATEMENT_DOWNLOAD",
            "SUCCESS",
            f"account {service.mask_account_number(account.account_number)} period {date_from} to {date_to} rows {len(rows)}",
        )
    except Exception as exc:
        db.rollback()
        # A successful response requires a durable audit record (BMS-SR-006).
        raise service.AppError(
            503, "STATEMENT_AUDIT_UNAVAILABLE",
            "Statement download is temporarily unavailable. Please try again.",
        ) from exc
    last4 = account.account_number[-4:]
    filename = f"statement-{last4}-{date_from.isoformat()}-{date_to.isoformat()}.csv"
    return Response(
        content=text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
