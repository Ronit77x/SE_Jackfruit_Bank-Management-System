"""Admin, audit and reporting endpoints. Owner: Member 4 (Vaibhav). Stories: US-24, US-25, US-26, US-27, US-28...

Planned endpoints (baseline Part A section 3):
  POST  /admin/users                create Teller
  PATCH /admin/users/{id}           deactivate / unlock
  GET   /admin/audit-logs           filter by user, action, date
  GET   /admin/reports/daily        daily transaction summary
"""
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app import crud
from app.constants import (
    ROLE_ADMIN,
    ROLE_TELLER,
    TXN_DEPOSIT,
    TXN_OPENING_DEPOSIT,
    TXN_TRANSFER_OUT,
    TXN_WITHDRAWAL,
    USER_ACTIVE,
    USER_INACTIVE,
    USER_LOCKED,
)
from app.database import get_db
from app.deps import require_roles
from app.models import Transaction, User
from app.security import hash_password
from app.services.audit_service import log_event

router = APIRouter(prefix="/admin", tags=["admin"])


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    user_id: int | None
    action: str
    outcome: str
    details: str


class TransactionSummary(BaseModel):
    count: int
    total_amount: Decimal


class DepositSummary(TransactionSummary):
    opening_deposits: TransactionSummary


class DailyReportResponse(BaseModel):
    report_date: date
    timezone: str
    generated_at: datetime
    deposits: DepositSummary
    withdrawals: TransactionSummary
    transfers: TransactionSummary


BANK_TIMEZONE = timezone(timedelta(hours=5, minutes=30))
BANK_TIMEZONE_NAME = "Asia/Kolkata"


def _report_day_bounds(value: str) -> tuple[date, datetime, datetime]:
    try:
        report_date = date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Date must be in YYYY-MM-DD format") from exc
    start_local = datetime.combine(report_date, time.min, tzinfo=BANK_TIMEZONE)
    next_day_local = start_local + timedelta(days=1)
    return (
        report_date,
        start_local.astimezone(timezone.utc).replace(tzinfo=None),
        next_day_local.astimezone(timezone.utc).replace(tzinfo=None),
    )


@router.get("/reports/daily", response_model=DailyReportResponse)
def daily_transaction_report(
    date: str = Query(..., description="Bank-local report date in YYYY-MM-DD format"),
    db: Session = Depends(get_db),
    admin=Depends(require_roles(ROLE_ADMIN)),
):
    """Return a bank-wide daily transaction summary for the selected IST day.

    OpeningDeposit rows, if present, are included in deposits and exposed as a
    transparent subcategory. TransferOut is the canonical transfer event so a
    transfer's matching TransferIn row is not double-counted.
    """
    report_date, start_utc, end_utc = _report_day_bounds(date)
    amount_sum = lambda condition: func.coalesce(func.sum(case((condition, Transaction.amount), else_=0)), 0)
    count_rows = lambda condition: func.coalesce(func.sum(case((condition, 1), else_=0)), 0)
    aggregates = db.execute(
        select(
            count_rows(Transaction.type.in_((TXN_DEPOSIT, TXN_OPENING_DEPOSIT))).label("deposit_count"),
            amount_sum(Transaction.type.in_((TXN_DEPOSIT, TXN_OPENING_DEPOSIT))).label("deposit_total"),
            count_rows(Transaction.type == TXN_OPENING_DEPOSIT).label("opening_count"),
            amount_sum(Transaction.type == TXN_OPENING_DEPOSIT).label("opening_total"),
            count_rows(Transaction.type == TXN_WITHDRAWAL).label("withdrawal_count"),
            amount_sum(Transaction.type == TXN_WITHDRAWAL).label("withdrawal_total"),
            count_rows(Transaction.type == TXN_TRANSFER_OUT).label("transfer_count"),
            amount_sum(Transaction.type == TXN_TRANSFER_OUT).label("transfer_total"),
        ).where(Transaction.created_at >= start_utc, Transaction.created_at < end_utc)
    ).one()

    def money(value) -> Decimal:
        return Decimal(str(value or 0)).quantize(Decimal("0.01"))

    def summary(count, total) -> TransactionSummary:
        return TransactionSummary(count=int(count or 0), total_amount=money(total))

    # BMS-SR-006: report generation is an administrative action; details contain
    # only the selected date and no customer, account or financial information.
    log_event(db, admin.id, "DAILY_REPORT_GENERATED", "SUCCESS", f"report_date={report_date.isoformat()}")
    return DailyReportResponse(
        report_date=report_date,
        timezone=BANK_TIMEZONE_NAME,
        generated_at=datetime.now(timezone.utc),
        deposits=DepositSummary(
            count=int(aggregates.deposit_count or 0),
            total_amount=money(aggregates.deposit_total),
            opening_deposits=summary(aggregates.opening_count, aggregates.opening_total),
        ),
        withdrawals=summary(aggregates.withdrawal_count, aggregates.withdrawal_total),
        transfers=summary(aggregates.transfer_count, aggregates.transfer_total),
    )


def _ist_day_boundary(value: str, *, end: bool) -> datetime:
    """Convert an IST calendar boundary to the UTC-naive form used by SQLite."""
    try:
        calendar_date = date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Date must be in YYYY-MM-DD format") from exc

    boundary = datetime.combine(calendar_date, time.max if end else time.min, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    return boundary.astimezone(timezone.utc).replace(tzinfo=None)


@router.get("/audit-logs", response_model=list[AuditLogResponse])
def list_audit_logs(
    user_id: str | None = Query(default=None),
    action: str | None = Query(default=None),
    date_from: str | None = Query(default=None, alias="from"),
    date_to: str | None = Query(default=None, alias="to"),
    limit: str = Query(default="100"),
    db: Session = Depends(get_db),
    admin=Depends(require_roles(ROLE_ADMIN)),
):
    try:
        parsed_user_id = int(user_id) if user_id is not None else None
        parsed_limit = int(limit)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="user_id and limit must be integers") from exc
    if parsed_user_id is not None and parsed_user_id < 1:
        raise HTTPException(status_code=422, detail="user_id must be at least 1")
    if parsed_limit < 1 or parsed_limit > 500:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 500")

    start = _ist_day_boundary(date_from, end=False) if date_from is not None else None
    finish = _ist_day_boundary(date_to, end=True) if date_to is not None else None
    if start is not None and finish is not None and start > finish:
        raise HTTPException(status_code=422, detail="from date must not be after to date")

    return crud.list_audit_logs(
        db,
        user_id=parsed_user_id,
        action=action,
        date_from=start,
        date_to=finish,
        limit=parsed_limit,
    )


class TellerCreate(BaseModel):
    username: str = Field(min_length=1, max_length=60)
    password: str = Field(min_length=8, description="At least 8 characters with uppercase, lowercase and digit")

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not any(char.islower() for char in value) or not any(char.isupper() for char in value) or not any(
            char.isdigit() for char in value
        ):
            raise ValueError("Password must contain uppercase, lowercase and a digit")
        return value


class UserAction(BaseModel):
    action: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str
    status: str
    failed_attempts: int
    must_change_password: bool


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_teller(
    payload: TellerCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_roles("Admin")),
):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=ROLE_TELLER,
        status=USER_ACTIVE,
        failed_attempts=0,
        must_change_password=True,
    )
    db.add(user)
    db.flush()
    log_event(db, admin.id, "CREATE_TELLER", "SUCCESS", f"Created Teller user id={user.id}")
    db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_teller(
    user_id: int,
    payload: UserAction,
    db: Session = Depends(get_db),
    admin=Depends(require_roles("Admin")),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.role != ROLE_TELLER:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only Teller users can be managed")

    if payload.action == "deactivate":
        user.status = USER_INACTIVE
        audit_action = "DEACTIVATE_TELLER"
    elif payload.action == "unlock":
        if user.status != USER_LOCKED:
            log_event(db, admin.id, "UNLOCK_TELLER", "FAILURE", f"Rejected unlock for Teller user id={user.id}")
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only locked users can be unlocked")
        user.status = USER_ACTIVE
        user.failed_attempts = 0
        audit_action = "UNLOCK_TELLER"
    else:
        log_event(db, admin.id, "ADMIN_USER_ACTION", "FAILURE", f"Rejected action for Teller user id={user.id}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action")

    db.flush()
    log_event(db, admin.id, audit_action, "SUCCESS", f"Updated Teller user id={user.id}")
    db.refresh(user)
    return user
