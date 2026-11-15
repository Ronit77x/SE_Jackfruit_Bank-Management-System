"""Account and customer endpoints.

Owner: Member 2 (Vijay). Stories: US-08, US-09, US-12.
"""

from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import (
    BaseModel,
    ConfigDict,
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
from app.models import Account, User
from app.security import mask_account_number
from app.services.account_service import open_account, update_account_status

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
