"""Create/read helpers for Transaction, AuditLog and Notification (US-16)."""
from decimal import Decimal

from app import crud
from app.constants import ACCOUNT_SAVINGS, TXN_DEPOSIT
from tests.test_crud import _customer


def _account(db):
    customer = _customer(db)
    return customer, crud.create_account(db, customer.id, ACCOUNT_SAVINGS, Decimal("1000"))


def test_transaction_create_read_and_list_newest_first(db):
    _, account = _account(db)
    first = crud.create_transaction(db, account.id, TXN_DEPOSIT, Decimal("100"), Decimal("1100"), receipt_no="R1")
    second = crud.create_transaction(db, account.id, TXN_DEPOSIT, Decimal("50"), Decimal("1150"), receipt_no="R2")
    assert crud.get_transaction(db, first.id).receipt_no == "R1"
    assert crud.get_transaction(db, 9999) is None
    assert [t.id for t in crud.list_transactions(db, account.id)] == [second.id, first.id]


def test_audit_log_create_read_and_filter(db):
    crud.create_audit_log(db, 1, "LOGIN", "SUCCESS", "ok")
    crud.create_audit_log(db, 2, "DEPOSIT", "FAILURE", "bad")
    entry = crud.create_audit_log(db, 1, "DEPOSIT", "SUCCESS")
    assert crud.get_audit_log(db, entry.id).action == "DEPOSIT"
    assert crud.get_audit_log(db, 9999) is None
    assert len(crud.list_audit_logs(db)) == 3
    assert len(crud.list_audit_logs(db, user_id=1)) == 2
    assert len(crud.list_audit_logs(db, action="DEPOSIT")) == 2
    assert len(crud.list_audit_logs(db, user_id=1, action="DEPOSIT")) == 1
    assert len(crud.list_audit_logs(db, limit=1)) == 1


def test_audit_log_and_transactions_have_no_update_or_delete_helpers():
    """Append-only records (BMS-NF-005): nobody should be able to edit them through crud."""
    names = dir(crud)
    for forbidden in ("update_audit_log", "delete_audit_log", "update_transaction", "delete_transaction"):
        assert forbidden not in names


def test_notification_create_read_list_and_update(db):
    customer, _ = _account(db)
    note = crud.create_notification(db, customer.id, "Rs 100 credited")
    crud.create_notification(db, customer.id, "Rs 50 debited")
    assert crud.get_notification(db, note.id).status == "LOGGED"
    assert len(crud.list_notifications(db, customer.id)) == 2
    assert crud.update_notification_status(db, note.id, "SENT").status == "SENT"
    assert crud.update_notification_status(db, 9999, "SENT") is None
