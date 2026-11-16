"""Account and customer endpoints.

Owner: Member 2 (Vijay). Stories: US-08, US-09, US-10, US-12, US-13, US-14.
"""

import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.constants import (
    ACCOUNT_ACTIVE,
    ACCOUNT_CLOSED,
    ACCOUNT_CURRENT,
    ACCOUNT_FROZEN,
    ACCOUNT_SAVINGS,
    ROLE_ADMIN,
    ROLE_CUSTOMER,
    ROLE_TELLER,
)
from app.database import get_db
from app.deps import require_roles
from app.errors import AppError
from app.models import Account, User
from app.security import mask_account_number
from app.services.account_service import (
    get_customer_accounts,
    open_account,
    update_account_status,
    update_customer_details,
)
from app.services.customer_search_service import (
    DEFAULT_SEARCH_LIMIT,
    get_relevant_accounts,
    mask_account_number as search_mask_account_number,
    search_customers,
)

router = APIRouter(tags=["accounts"])


# ---------------------------------------------------------------------------
# US-08: Open Account Schemas & Endpoint
# ---------------------------------------------------------------------------

class OpenAccountRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    account_type: str = Field(pattern="^(Savings|Current)$")
    deposit: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    customer_id: int | None = Field(default=None, gt=0)

    # Required for a new customer; ignored when customer_id is supplied.
    name: str | None = Field(default=None, min_length=1, max_length=120)
    date_of_birth: date | None = None
    address: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, min_length=1, max_length=20)
    email: str | None = Field(default=None, min_length=1, max_length=120)
    id_proof_number: str | None = Field(
        default=None, min_length=1, max_length=255
    )


@router.post("/accounts", status_code=status.HTTP_201_CREATED)
def create_account(
    payload: OpenAccountRequest,
    db: Annotated[Session, Depends(get_db)],
    teller=Depends(require_roles(ROLE_TELLER)),
):
    """Open a Savings or Current account and issue a first-time login."""
    try:
        result = open_account(
            db=db,
            account_type=payload.account_type,
            deposit=payload.deposit,
            customer_id=payload.customer_id,
            name=payload.name,
            date_of_birth=payload.date_of_birth,
            address=payload.address,
            phone=payload.phone,
            email=payload.email,
            id_proof_number=payload.id_proof_number,
            actor_id=getattr(teller, "id", None),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A conflicting customer or account record already exists.",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to open the account. Please try again.",
        ) from exc

    if result["temporary_password"] is None:
        result.pop("temporary_password")

    return result


# ---------------------------------------------------------------------------
# US-09: View Account & Balance Endpoint
# ---------------------------------------------------------------------------

@router.get("/accounts")
def get_my_accounts(
    db: Annotated[Session, Depends(get_db)],
    user=Depends(require_roles(ROLE_CUSTOMER)),
):
    """Return the authenticated customer's account details and balances."""

    if user.role != ROLE_CUSTOMER or user.customer_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated customer required.",
        )

    accounts = db.scalars(
        select(Account).where(Account.customer_id == user.customer_id)
    ).all()

    return {
        "accounts": [
            {
                "account_id": account.id,
                "account_number": mask_account_number(account.account_number),
                "account_type": account.type,
                "balance": str(account.balance),
                "status": account.status,
            }
            for account in accounts
        ]
    }


# ---------------------------------------------------------------------------
# US-10: Update Customer Contact Details Schemas & Endpoint
# ---------------------------------------------------------------------------

class UpdateCustomerRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    phone: str | None = None
    email: EmailStr | None = None
    address: str | None = None

    @field_validator("phone", "email", "address", mode="before")
    @classmethod
    def reject_explicit_null(cls, value: object, info: ValidationInfo) -> object:
        """Reject explicit JSON null values for update fields."""
        if value is None:
            raise ValueError(f"{info.field_name} cannot be null.")
        return value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        """Validate phone number: 10 to 15 digits, optional leading '+'."""
        if value is not None:
            trimmed = value.strip()
            if not re.fullmatch(r"^\+?[1-9]\d{9,14}$", trimmed):
                raise ValueError(
                    "Phone number must contain 10 to 15 digits and may start with '+'."
                )
            return trimmed
        return value

    @field_validator("address")
    @classmethod
    def validate_address(cls, value: str | None) -> str | None:
        """Validate address: non-empty, non-whitespace, max 255 chars."""
        if value is not None:
            trimmed = value.strip()
            if not trimmed:
                raise ValueError("Address cannot be empty or whitespace-only.")
            if len(trimmed) > 255:
                raise ValueError("Address cannot exceed 255 characters.")
            return trimmed
        return value

    @model_validator(mode="after")
    def check_at_least_one_field(self) -> "UpdateCustomerRequest":
        """Ensure at least one field is provided for update."""
        if (
            self.phone is None
            and self.email is None
            and self.address is None
        ):
            raise ValueError(
                "At least one field (phone, email, address) must be provided."
            )
        return self


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    date_of_birth: date
    address: str
    phone: str
    email: str
    created_at: datetime


@router.put(
    "/customers/{customer_id}",
    response_model=CustomerResponse,
    status_code=status.HTTP_200_OK,
)
def update_customer_endpoint(
    customer_id: int,
    payload: UpdateCustomerRequest,
    db: Annotated[Session, Depends(get_db)],
    teller: Annotated[User, Depends(require_roles(ROLE_TELLER))],
):
    """Update contact details (phone, email, address) for an existing customer (BMS-F-011)."""
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="NO_FIELDS_PROVIDED",
            message="At least one field must be provided to update.",
        )

    updated_customer = update_customer_details(
        db=db,
        customer_id=customer_id,
        updates=updates,
        teller_id=getattr(teller, "id", None),
    )
    return updated_customer


# ---------------------------------------------------------------------------
# US-12: Account Status Management (Freeze / Unfreeze / Close)
# ---------------------------------------------------------------------------

class AccountStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    status: str | None = None
    action: str | None = None

    @field_validator("status", "action", mode="before")
    @classmethod
    def reject_explicit_null(cls, value: object, info: ValidationInfo) -> object:
        if value is None:
            raise ValueError(f"{info.field_name} cannot be null.")
        return value

    @model_validator(mode="after")
    def resolve_target_status(self) -> "AccountStatusUpdateRequest":
        if self.status is None and self.action is None:
            raise ValueError("Either 'status' or 'action' must be provided.")

        if self.status is not None and self.action is not None:
            raise ValueError("Provide either 'status' or 'action', not both.")

        raw = self.status if self.status is not None else self.action
        if raw is None or not str(raw).strip():
            raise ValueError("Status or action cannot be empty.")

        cleaned = str(raw).strip().lower()
        mapping = {
            "freeze": ACCOUNT_FROZEN,
            "frozen": ACCOUNT_FROZEN,
            "unfreeze": ACCOUNT_ACTIVE,
            "active": ACCOUNT_ACTIVE,
            "activate": ACCOUNT_ACTIVE,
            "close": ACCOUNT_CLOSED,
            "closed": ACCOUNT_CLOSED,
        }

        if cleaned not in mapping:
            raise ValueError(
                f"Invalid status or action '{raw}'. Allowed: Active, Frozen, Closed (or freeze, unfreeze, close)."
            )

        self.status = mapping[cleaned]
        return self


class AccountStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_number: str
    status: str
    balance: Decimal
    type: str


@router.patch(
    "/accounts/{account_id}/status",
    response_model=AccountStatusResponse,
    status_code=status.HTTP_200_OK,
)
def update_account_status_endpoint(
    account_id: str,
    payload: AccountStatusUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_roles(ROLE_ADMIN))],
):
    """Freeze, unfreeze, or close an account (BMS-F-012). Admin only."""
    account = update_account_status(
        db=db,
        account_identifier=account_id,
        target_status=payload.status,
        admin_id=getattr(admin, "id", None),
    )
    return account


@router.post(
    "/accounts/{account_id}/freeze",
    response_model=AccountStatusResponse,
    status_code=status.HTTP_200_OK,
)
def freeze_account_endpoint(
    account_id: str,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_roles(ROLE_ADMIN))],
):
    """Freeze an active account (BMS-F-012). Admin only."""
    return update_account_status(
        db=db,
        account_identifier=account_id,
        target_status=ACCOUNT_FROZEN,
        admin_id=getattr(admin, "id", None),
    )


@router.post(
    "/accounts/{account_id}/unfreeze",
    response_model=AccountStatusResponse,
    status_code=status.HTTP_200_OK,
)
def unfreeze_account_endpoint(
    account_id: str,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_roles(ROLE_ADMIN))],
):
    """Unfreeze a frozen account (BMS-F-012). Admin only."""
    return update_account_status(
        db=db,
        account_identifier=account_id,
        target_status=ACCOUNT_ACTIVE,
        admin_id=getattr(admin, "id", None),
    )


@router.post(
    "/accounts/{account_id}/close",
    response_model=AccountStatusResponse,
    status_code=status.HTTP_200_OK,
)
def close_account_endpoint(
    account_id: str,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_roles(ROLE_ADMIN))],
):
    """Close an account with zero balance (BMS-F-012). Admin only."""
    return update_account_status(
        db=db,
        account_identifier=account_id,
        target_status=ACCOUNT_CLOSED,
        admin_id=getattr(admin, "id", None),
    )


# ---------------------------------------------------------------------------
# US-13: Search Customers & Accounts Schemas & Endpoint
# ---------------------------------------------------------------------------

class SearchAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    accountNumber: str
    type: str
    status: str
    balance: Decimal


class CustomerSearchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str
    email: str
    accounts: list[SearchAccountResponse] = Field(default_factory=list)


@router.get(
    "/customers",
    response_model=list[CustomerSearchResponse],
    status_code=status.HTTP_200_OK,
)
def search_customers_endpoint(
    q: Annotated[str | None, Query(description="Search by customer name, phone number, or account number")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum number of search results to return")] = DEFAULT_SEARCH_LIMIT,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(ROLE_TELLER)),
):
    """Search customers by full/partial name, phone number, or account number (BMS-F-014). Teller only."""
    query_str = q or ""
    customers = search_customers(db=db, query=query_str, limit=limit)

    results: list[CustomerSearchResponse] = []
    for c in customers:
        relevant_accounts = get_relevant_accounts(c, query_str)
        acc_list = [
            SearchAccountResponse(
                id=acc.id,
                accountNumber=search_mask_account_number(acc.account_number),
                type=acc.type,
                status=acc.status,
                balance=acc.balance,
            )
            for acc in relevant_accounts
        ]
        results.append(
            CustomerSearchResponse(
                id=c.id,
                name=c.name,
                phone=c.phone,
                email=c.email,
                accounts=acc_list,
            )
        )
    return results


# ---------------------------------------------------------------------------
# US-14: Fund Transfer Account Summary & UI Endpoints (BMS-NF-004)
# ---------------------------------------------------------------------------

STATIC_TRANSFER_HTML = Path(__file__).resolve().parent.parent / "static" / "transfer.html"
FRONTEND_TRANSFER_HTML = Path(__file__).resolve().parent.parent.parent / "frontend" / "transfer.html"


class CustomerAccountSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    accountNumber: str
    maskedAccountNumber: str
    type: str
    status: str
    balance: Decimal


@router.get(
    "/accounts/me",
    response_model=list[CustomerAccountSummary],
    status_code=status.HTTP_200_OK,
    tags=["accounts"],
)
@router.get(
    "/accounts/my-accounts",
    response_model=list[CustomerAccountSummary],
    status_code=status.HTTP_200_OK,
    tags=["accounts"],
)
def list_my_accounts(
    user: Annotated[User, Depends(require_roles(ROLE_CUSTOMER))],
    db: Annotated[Session, Depends(get_db)],
):
    """Retrieve accounts owned by the authenticated customer for fund transfer (BMS-NF-004, US-14)."""
    if not user.customer_id:
        return []

    accounts = get_customer_accounts(db, user.customer_id)
    return [
        CustomerAccountSummary(
            id=acc.id,
            accountNumber=acc.account_number,
            maskedAccountNumber=mask_account_number(acc.account_number),
            type=acc.type,
            status=acc.status,
            balance=acc.balance,
        )
        for acc in accounts
    ]


@router.get("/transfer", response_class=HTMLResponse, tags=["ui"])
@router.get("/transfer-ui", response_class=HTMLResponse, tags=["ui"])
def get_transfer_ui():
    """Serve the customer fund transfer web interface (BMS-NF-004, TC-UX-01)."""
    target = STATIC_TRANSFER_HTML if STATIC_TRANSFER_HTML.exists() else FRONTEND_TRANSFER_HTML
    if target.exists():
        content = target.read_text(encoding="utf-8")
        return HTMLResponse(content=content, status_code=status.HTTP_200_OK)
    return HTMLResponse(
        content="<h1>Transfer UI not found</h1>",
        status_code=status.HTTP_404_NOT_FOUND,
    )

