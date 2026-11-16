"""Audit logging must never leave the books inconsistent (BMS-SR-006, BMS-NF-003)."""
from decimal import Decimal

import pytest

from app import crud
from app.errors import AppError
from app.models import AuditLog, Transaction
from app.services import transaction_service as service
from tests.test_crud import _customer


def _account(db, balance="10000"):
    return crud.create_account(db, _customer(db).id, "Savings", Decimal(balance))


def test_audit_row_is_saved_together_with_the_movement(db):
    account = _account(db)
    service.deposit(db, account.account_number, Decimal("500"), 1)
    rows = db.query(AuditLog).filter_by(action="DEPOSIT", outcome="SUCCESS").all()
    assert len(rows) == 1
    assert account.account_number not in rows[0].details  # only the masked number is stored
    assert account.account_number[-4:] in rows[0].details


def test_if_the_audit_row_cannot_be_written_nothing_changes(db, monkeypatch):
    """Fail closed: no money movement without its audit record."""
    account = _account(db)

    def broken_audit(*args, **kwargs):
        raise RuntimeError("audit table unavailable")

    monkeypatch.setattr(service, "_audit", broken_audit)
    with pytest.raises(RuntimeError):
        service.deposit(db, account.account_number, Decimal("500"), 1)

    db.expire_all()
    assert crud.get_account_by_number(db, account.account_number).balance == Decimal("10000.00")
    assert db.query(Transaction).count() == 0


def test_a_problem_logging_a_rejected_request_does_not_hide_the_real_error(db, monkeypatch):
    account = _account(db, "1500")

    def broken_log_event(*args, **kwargs):
        raise RuntimeError("audit table unavailable")

    monkeypatch.setattr(service, "log_event", broken_log_event)
    with pytest.raises(AppError) as error:
        service.withdraw(db, account.account_number, Decimal("1000"), 1)  # would go below the minimum balance
    assert error.value.status_code == 422
    assert error.value.code == "INSUFFICIENT_FUNDS"


def test_failed_transfer_leaves_one_failure_audit_row_and_no_success_row(db):
    source = _account(db, "1500")
    destination = _account(db, "2000")
    with pytest.raises(AppError):
        service.transfer(db, source.account_number, destination.account_number, Decimal("1000"), 1)
    outcomes = [(row.action, row.outcome) for row in db.query(AuditLog).all()]
    assert outcomes == [("TRANSFER", "FAILURE")]
