"""Account and customer endpoints. Owner: Member 2 (Vijay). Stories: US-08, US-09, US-10, US-12, US-13, US-14.

Planned endpoints (baseline Part A section 3):
  POST  /accounts                 open account (+ customer login with temporary password)  (Teller)
  PUT   /customers/{id}           update contact details                                  (Teller)
  PATCH /accounts/{id}/status     freeze / unfreeze / close                               (Admin)
  GET   /accounts/{id}            details + balance (own accounts only)                   (Customer)
  GET   /customers?q=             search                                                  (Teller)
  GET   /accounts/me              list own accounts for fund transfer                     (Customer)
  GET   /transfer                 transfer money web interface                            (Web UI)
"""

from decimal import Decimal
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.constants import ROLE_CUSTOMER
from app.database import get_db
from app.deps import require_roles
from app.models import User
from app.services.account_service import get_customer_accounts, mask_account_number

router = APIRouter(tags=["accounts"])

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
    """Retrieve accounts owned by the authenticated customer (BMS-NF-004, US-14)."""
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
    if FRONTEND_TRANSFER_HTML.exists():
        content = FRONTEND_TRANSFER_HTML.read_text(encoding="utf-8")
        return HTMLResponse(content=content, status_code=status.HTTP_200_OK)
    return HTMLResponse(
        content="<h1>Transfer UI not found</h1>",
        status_code=status.HTTP_404_NOT_FOUND,
    )
