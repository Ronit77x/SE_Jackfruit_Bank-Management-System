
"""Shared authentication and role-check dependencies."""

from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.constants import SESSION_IDLE_MINUTES
from app.database import get_db
from app.models import User
from app.routers.auth import _sessions


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Return the database user associated with a valid Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[7:].strip()
    session = _sessions.get(token)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
            headers={"WWW-Authenticate": "Bearer"},
        )

    now = datetime.now(timezone.utc)
    if session["expires_at"] <= now:
        _sessions.pop(token, None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Enforce the 10-minute idle timeout by tracking last activity.
    last_activity = session.get("last_activity", session["expires_at"] - timedelta(minutes=SESSION_IDLE_MINUTES))
    if now - last_activity >= timedelta(minutes=SESSION_IDLE_MINUTES):
        _sessions.pop(token, None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired due to inactivity",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == session["user_id"]).first()
    if user is None or user.status != "Active":
        _sessions.pop(token, None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is unavailable",
            headers={"WWW-Authenticate": "Bearer"},
        )

    session["last_activity"] = now
    session["expires_at"] = now + timedelta(minutes=SESSION_IDLE_MINUTES)
    return user


def require_roles(*allowed_roles: str):
    """Allow access only when the authenticated user has an allowed role."""

    def checker(user=Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return checker
