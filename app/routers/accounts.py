"""Account and customer endpoints. Owner: Member 2 (Vijay). Stories: US-08, US-09, US-10, US-12, US-13.

Planned endpoints (baseline Part A section 3):
  POST  /accounts                 open account (+ customer login with temporary password)  (Teller)
  PUT   /customers/{id}           update contact details                                  (Teller)
  PATCH /accounts/{id}/status     freeze / unfreeze / close                               (Admin)
  GET   /accounts/{id}            details + balance (own accounts only)                   (Customer)
  GET   /customers?q=             search                                                  (Teller)
"""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator, model_validator
from sqlalchemy.orm import Session

from app.constants import ACCOUNT_ACTIVE, ACCOUNT_CLOSED, ACCOUNT_FROZEN, ROLE_ADMIN
from app.database import get_db
from app.deps import require_roles
from app.models import User
from app.services.account_service import update_account_status

router = APIRouter(tags=["accounts"])


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
        target_status=payload.status,  # Guaranteed valid by validator
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
