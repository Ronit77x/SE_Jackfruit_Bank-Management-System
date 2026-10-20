"""Audit logging helper. Owner: Member 4 (Vaibhav), story US-25 (BMS-SR-006).

Working starting point so everybody can already call `log_event(...)`.
Vaibhav extends it (but keeps the function name and arguments).
Rules: never pass passwords, temporary passwords or full account numbers in `details`.
"""
import re

from sqlalchemy.orm import Session

from app.models import AuditLog

_VALID_OUTCOMES = frozenset({"SUCCESS", "FAILURE", "DENIED"})
_PASSWORD_DETAIL = re.compile(
    r"""(?ix)
    (?P<prefix>
        (?:"|')?\b(?:password|passwd|pwd|passcode|secret)\b(?:"|')?
        \s*[:=]\s*
    )
    (?P<value>
        "(?:\\.|[^"\\])*"
        | '(?:\\.|[^'\\])*'
        | [^,;\s]+
    )
    """
)
_ACCOUNT_NUMBER = re.compile(r"(?<!\d)\d{10}(?!\d)")


def _sanitize_details(details: str) -> str:
    """Remove credentials and complete account numbers from audit details."""
    sanitized = _PASSWORD_DETAIL.sub(r"\g<prefix>[REDACTED]", details)
    return _ACCOUNT_NUMBER.sub("[ACCOUNT_NUMBER_REDACTED]", sanitized)


def log_event(db: Session, user_id: int | None, action: str, outcome: str, details: str = "") -> None:
    if outcome not in _VALID_OUTCOMES:
        raise ValueError("Unsupported audit outcome")

    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            outcome=outcome,
            details=_sanitize_details(details),
        )
    )
    db.commit()
