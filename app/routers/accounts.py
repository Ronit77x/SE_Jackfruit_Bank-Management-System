
"""Account and customer endpoints. Owner: Member 2 (Vijay)."""

from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.constants import ACCOUNT_CURRENT, ACCOUNT_SAVINGS
from app.database import get_db
from app.deps import require_roles
from app.services.account_service import open_account
from app.services.audit_service import log_event

router = APIRouter(tags=["accounts"])


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
    teller=Depends(require_roles("Teller")),
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

    try:
        log_event(
            db,
            user_id=getattr(teller, "id", None),
            action="ACCOUNT_OPENED",
            outcome="SUCCESS",
            details=f"Customer ID {result['customer_id']}; account type {result['account_type']}",
        )
    except Exception:
        # Audit helper currently commits independently; don't expose internal errors.
        # Account creation has already committed at this point.
        pass

    # Never include a password field for an existing customer's account.
    if result["temporary_password"] is None:
        result.pop("temporary_password")

    return result
