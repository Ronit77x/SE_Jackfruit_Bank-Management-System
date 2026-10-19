"""Audit logging helper. Owner: Member 4 (Vaibhav), story US-25 (BMS-SR-006).

Working starting point so everybody can already call `log_event(...)`.
Vaibhav extends it (but keeps the function name and arguments).
Rules: never pass passwords, temporary passwords or full account numbers in `details`.
"""
from sqlalchemy.orm import Session

from app.models import AuditLog


def log_event(db: Session, user_id: int | None, action: str, outcome: str, details: str = "") -> None:
    db.add(AuditLog(user_id=user_id, action=action, outcome=outcome, details=details))
    db.commit()
