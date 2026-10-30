
"""Authentication endpoints for US-01 and related authentication stories."""

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.constants import USER_ACTIVE, USER_LOCKED
from app.database import get_db
from app.models import User
from app.security import verify_password
from app.services.audit_service import log_event

router = APIRouter(prefix="/auth", tags=["auth"])

# Temporary in-memory sessions. These are lost when the server restarts.
# A persistent session store can be introduced in a later change.
_sessions: dict[str, dict] = {}
SESSION_LIFETIME = timedelta(minutes=10)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=60)
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    token: str
    role: str
    mustChangePassword: bool


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

    # Keep the same error for unknown usernames and incorrect passwords.
    if user is None or not verify_password(payload.password, user.password_hash):
        log_event(
            db,
            user.id if user else None,
            "LOGIN",
            "FAILURE",
            "Invalid credentials",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if user.status == USER_LOCKED:
        log_event(db, user.id, "LOGIN", "DENIED", "Account locked")
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account is locked",
        )

    if user.status != USER_ACTIVE:
        log_event(db, user.id, "LOGIN", "DENIED", "Account inactive")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

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
def logout(
    authorization: str | None = Header(default=None),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[7:].strip()

    if token not in _sessions:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _sessions.pop(token, None)
    return {"message": "Logged out"}
