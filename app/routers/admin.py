"""Admin, audit and reporting endpoints. Owner: Member 4 (Vaibhav). Stories: US-24, US-25, US-26, US-27, US-28...

Planned endpoints (baseline Part A section 3):
  POST  /admin/users                create Teller
  PATCH /admin/users/{id}           deactivate / unlock
  GET   /admin/audit-logs           filter by user, action, date
  GET   /admin/reports/daily        daily transaction summary
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.constants import ROLE_TELLER, USER_ACTIVE, USER_INACTIVE, USER_LOCKED
from app.database import get_db
from app.deps import require_roles
from app.models import User
from app.security import hash_password
from app.services.audit_service import log_event

router = APIRouter(prefix="/admin", tags=["admin"])


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
