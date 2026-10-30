
"""Authentication endpoints for login, logout, and account lockout."""

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.constants import MAX_FAILED_LOGINS, ROLE_ADMIN, USER_ACTIVE, USER_LOCKED
from app.database import get_db
from app.models import User
from app.security import verify_password
from app.services.audit_service import log_event

router = APIRouter(prefix="/auth", tags=["auth"])

_sessions: dict[str, dict] = {}
SESSION_LIFETIME = timedelta(minutes=10)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=60)
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    token: str
    role: str
    mustChangePassword: bool


class UnlockRequest(BaseModel):
    username: str = Field(min_length=1, max_length=60)


def _remove_expired_sessions() -> None:
    now = datetime.now(timezone.utc)
    expired_tokens = [
        token for token, session in _sessions.items()
        if session["expires_at"] <= now
    ]
    for token in expired_tokens:
        del _sessions[token]


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    username = payload.username.strip()
    user = db.query(User).filter(User.username == username).first()

    if user is None:
        log_event(db, None, "LOGIN", "FAILURE", "Invalid credentials")
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if user.status == USER_LOCKED:
        log_event(db, user.id, "LOGIN", "DENIED", "Account locked")
        raise HTTPException(status_code=423, detail="Account is locked")

    if user.status != USER_ACTIVE:
        log_event(db, user.id, "LOGIN", "DENIED", "Account inactive")
        raise HTTPException(status_code=403, detail="Account is inactive")

    if not verify_password(payload.password, user.password_hash):
        user.failed_attempts += 1

        if user.failed_attempts >= MAX_FAILED_LOGINS:
            user.status = USER_LOCKED
            log_event(
                db, user.id, "ACCOUNT_LOCKOUT", "SUCCESS",
                "Account locked after consecutive failed login attempts",
            )
        else:
            log_event(db, user.id, "LOGIN", "FAILURE", "Invalid credentials")

        db.commit()
        raise HTTPException(status_code=401, detail="Invalid username or password")

    user.failed_attempts = 0
    db.commit()

    _remove_expired_sessions()
    token = secrets.token_urlsafe(32)
    _sessions[token] = {
        "user_id": user.id,
        "expires_at": datetime.now(timezone.utc) + SESSION_LIFETIME,
    }

    log_event(db, user.id, "LOGIN", "SUCCESS", "Login successful")

    return LoginResponse(
        token=token,
        role=user.role,
        mustChangePassword=user.must_change_password,
    )


@router.post("/logout")
def logout(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[7:].strip()

    if token not in _sessions:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _sessions.pop(token, None)
    return {"message": "Logged out"}


def get_admin_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    from fastapi import HTTPException
    from app.deps import get_current_user, require_roles

    user = get_current_user(authorization=authorization, db=db)
    checker = require_roles(ROLE_ADMIN)
    return checker(user)


@router.post("/unlock")
def unlock_account(
    payload: UnlockRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    username = payload.username.strip()
    user = db.query(User).filter(User.username == username).first()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user.status != USER_LOCKED:
        raise HTTPException(status_code=409, detail="Account is not locked")

    user.status = USER_ACTIVE
    user.failed_attempts = 0
    db.commit()

    log_event(
        db, admin.id, "ACCOUNT_UNLOCK", "SUCCESS",
        f"Administrator unlocked account for user ID {user.id}",
    )

    return {"message": "Account unlocked"}
