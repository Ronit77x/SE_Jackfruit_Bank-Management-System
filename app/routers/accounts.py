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

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.constants import ROLE_TELLER
from app.database import get_db
from app.deps import require_roles
from app.models import User
from app.services.customer_search_service import (
    get_relevant_accounts,
    mask_account_number,
    search_customers,
)

router = APIRouter(tags=["accounts"])


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
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(ROLE_TELLER)),
):
    """Search customers by full/partial name, phone number, or account number (BMS-F-014). Teller only."""
    query_str = q or ""
    customers = search_customers(db=db, query=query_str)

    results: list[CustomerSearchResponse] = []
    for c in customers:
        relevant_accounts = get_relevant_accounts(c, query_str)
        acc_list = [
            SearchAccountResponse(
                id=acc.id,
                accountNumber=mask_account_number(acc.account_number),
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
