"""Customer notification read endpoint (US-29)."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app import crud
from app.constants import ROLE_CUSTOMER
from app.database import get_db
from app.deps import require_roles

router = APIRouter(tags=["notifications"])


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    message: str
    status: str
    created_at: datetime


@router.get("/notifications", response_model=list[NotificationResponse])
def list_customer_notifications(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ROLE_CUSTOMER)),
):
    """Return only notifications belonging to the authenticated customer."""
    customer_id = getattr(current_user, "customer_id", None)
    if customer_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer account is not associated with a customer record",
        )

    return crud.list_notifications(db, customer_id)
