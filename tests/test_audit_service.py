"""Tests for US-25 audit event validation and detail protection."""
import inspect

import pytest

from app.models import AuditLog
from app.services.audit_service import log_event


@pytest.mark.parametrize("outcome", ["SUCCESS", "FAILURE", "DENIED"])
def test_log_event_persists_each_supported_outcome(db, outcome):
    log_event(db, user_id=7, action="LOGIN", outcome=outcome, details="login attempt")

    record = db.query(AuditLog).one()
    assert record.user_id == 7
    assert record.action == "LOGIN"
    assert record.outcome == outcome
    assert record.details == "login attempt"
    assert record.timestamp is not None


def test_log_event_rejects_unsupported_outcome_without_creating_row(db):
    with pytest.raises(ValueError, match="Unsupported audit outcome"):
        log_event(db, user_id=7, action="LOGIN", outcome="PENDING", details="login attempt")

    assert db.query(AuditLog).count() == 0


def test_log_event_redacts_password_like_details_in_stored_record(db):
    log_event(
        db,
        user_id=7,
        action="PASSWORD_CHANGE",
        outcome="SUCCESS",
        details="password=CorrectHorseBatteryStaple result=changed",
    )

    stored_details = db.query(AuditLog).one().details
    assert "CorrectHorseBatteryStaple" not in stored_details
    assert "password=[REDACTED]" in stored_details
    assert "result=changed" in stored_details


@pytest.mark.parametrize(
    ("details", "sensitive_value"),
    [
        ("password: colon secret", "colon secret"),
        ('"password": "my secret value"', "my secret value"),
        ("password='single quoted secret value'", "single quoted secret value"),
        ('password="double quoted secret value"', "double quoted secret value"),
    ],
)
def test_log_event_redacts_quoted_and_spaced_password_details(db, details, sensitive_value):
    log_event(db, user_id=7, action="PASSWORD_CHANGE", outcome="SUCCESS", details=details)

    stored_details = db.query(AuditLog).one().details
    assert sensitive_value not in stored_details
    assert "[REDACTED]" in stored_details


def test_log_event_redacts_complete_account_number_in_stored_record(db):
    log_event(
        db,
        user_id=7,
        action="TRANSFER",
        outcome="SUCCESS",
        details="from_account=1234567890 amount=2500",
    )

    stored_details = db.query(AuditLog).one().details
    assert "1234567890" not in stored_details
    assert "from_account=[ACCOUNT_NUMBER_REDACTED]" in stored_details
    assert "amount=2500" in stored_details


def test_log_event_preserves_ordinary_details(db):
    details = "customer_id=42 reason=manual review completed"

    log_event(db, user_id=None, action="ACCOUNT_REVIEW", outcome="DENIED", details=details)

    assert db.query(AuditLog).one().details == details


def test_log_event_signature_remains_compatible():
    parameters = list(inspect.signature(log_event).parameters)

    assert parameters == ["db", "user_id", "action", "outcome", "details"]
