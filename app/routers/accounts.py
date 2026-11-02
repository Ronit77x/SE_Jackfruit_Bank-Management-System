"""Account and customer endpoints. Owner: Member 2 (Vijay). Stories: US-08, US-09, US-10, US-12, US-13.

Planned endpoints (baseline Part A section 3):
  POST  /accounts                 open account (+ customer login with temporary password)  (Teller)
  PUT   /customers/{id}           update contact details                                  (Teller)
  PATCH /accounts/{id}/status     freeze / unfreeze / close                               (Admin)
  GET   /accounts/{id}            details + balance (own accounts only)                   (Customer)
  GET   /customers?q=             search                                                  (Teller)
"""

import re
from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    ValidationInfo,
    field_validator,
    model_validator,
)
from sqlalchemy.orm import Session

from app.constants import ROLE_TELLER
from app.database import get_db
from app.deps import require_roles
from app.errors import AppError
from app.models import User
from app.services.account_service import update_customer_details

router = APIRouter(tags=["accounts"])


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
