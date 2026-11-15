"""Account and customer endpoints.

Owner: Member 2 (Vijay). Stories: US-08, US-09, US-10.
"""

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
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

from app.constants import ACCOUNT_CURRENT, ACCOUNT_SAVINGS, ROLE_CUSTOMER, ROLE_TELLER
from app.database import get_db
from app.deps import require_roles
from app.errors import AppError
from app.models import Account, User
from app.security import mask_account_number
from app.services.account_service import open_account, update_customer_details

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
