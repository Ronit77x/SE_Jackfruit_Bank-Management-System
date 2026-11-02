"""Tests for US-12: Freeze, Unfreeze and Close Bank Accounts (BMS-F-012, TC-Acc-03).

Owner: Member 2 (Vijay).
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from app.constants import (
    ACCOUNT_ACTIVE,
    ACCOUNT_CLOSED,
    ACCOUNT_FROZEN,
    ACCOUNT_SAVINGS,
    ROLE_ADMIN,
    ROLE_CUSTOMER,
    ROLE_TELLER,
)
from app.models import Account, AuditLog, Customer
from tests.auth_helpers import act_as


@pytest.fixture()
def sample_customer(db):
    customer = Customer(
        name="Deepa Sharma",
        date_of_birth=date(1992, 8, 20),
        address="12 MG Road, Bengaluru",
        phone="9876543210",
        email="deepa@example.com",
        id_proof_number="ID-PROOF-DEEPA-01",
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@pytest.fixture()
def active_account(db, sample_customer):
    account = Account(
        account_number="1000000099",
        customer_id=sample_customer.id,
        type=ACCOUNT_SAVINGS,
        balance=Decimal("5000.00"),
        status=ACCOUNT_ACTIVE,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@pytest.fixture()
def zero_balance_account(db, sample_customer):
    account = Account(
        account_number="1000000098",
        customer_id=sample_customer.id,
        type=ACCOUNT_SAVINGS,
        balance=Decimal("0.00"),
        status=ACCOUNT_ACTIVE,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@pytest.fixture()
def frozen_account(db, sample_customer):
    account = Account(
        account_number="1000000097",
        customer_id=sample_customer.id,
        type=ACCOUNT_SAVINGS,
        balance=Decimal("2000.00"),
        status=ACCOUNT_FROZEN,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@pytest.fixture()
def closed_account(db, sample_customer):
    account = Account(
        account_number="1000000095",
        customer_id=sample_customer.id,
        type=ACCOUNT_SAVINGS,
        balance=Decimal("0.00"),
        status=ACCOUNT_CLOSED,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


# ==================== A. FREEZE ====================

def test_admin_successfully_freezes_active_account(client, db, active_account):
    act_as(ROLE_ADMIN, user_id=1)

    response = client.patch(
        f"/accounts/{active_account.account_number}/status",
        json={"status": "Frozen"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["account_number"] == active_account.account_number
    assert data["status"] == ACCOUNT_FROZEN

    # Verify DB persistence
    db.expire_all()
    reloaded = db.get(Account, active_account.id)
    assert reloaded.status == ACCOUNT_FROZEN


def test_admin_freezes_account_by_integer_id(client, db, active_account):
    act_as(ROLE_ADMIN, user_id=1)

    response = client.patch(
        f"/accounts/{active_account.id}/status",
        json={"action": "freeze"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == ACCOUNT_FROZEN


def test_freeze_via_convenience_endpoint(client, db, active_account):
    act_as(ROLE_ADMIN, user_id=1)

    response = client.post(f"/accounts/{active_account.account_number}/freeze")
    assert response.status_code == 200
    assert response.json()["status"] == ACCOUNT_FROZEN


def test_freeze_rejected_for_teller(client, db, active_account):
    act_as(ROLE_TELLER, user_id=2)
    response = client.patch(
        f"/accounts/{active_account.account_number}/status",
        json={"status": "Frozen"},
    )
    assert response.status_code == 403


def test_freeze_rejected_for_customer(client, db, active_account):
    act_as(ROLE_CUSTOMER, user_id=3, customer_id=active_account.customer_id)
    response = client.patch(
        f"/accounts/{active_account.account_number}/status",
        json={"status": "Frozen"},
    )
    assert response.status_code == 403


def test_freeze_unauthenticated_returns_401(client, active_account):
    response = client.patch(
        f"/accounts/{active_account.account_number}/status",
        json={"status": "Frozen"},
    )
    assert response.status_code == 401


def test_freeze_nonexistent_account_returns_404(client):
    act_as(ROLE_ADMIN, user_id=1)
    response = client.patch(
        "/accounts/9999999999/status",
        json={"status": "Frozen"},
    )
    assert response.status_code == 404
    assert response.json()["code"] == "ACCOUNT_NOT_FOUND"


def test_already_frozen_account_cannot_be_frozen_again(client, db, frozen_account):
    act_as(ROLE_ADMIN, user_id=1)
    response = client.patch(
        f"/accounts/{frozen_account.account_number}/status",
        json={"status": "Frozen"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_STATUS_TRANSITION"


# ==================== B. UNFREEZE ====================

def test_admin_successfully_unfreezes_frozen_account(client, db, frozen_account):
    act_as(ROLE_ADMIN, user_id=1)

    response = client.patch(
        f"/accounts/{frozen_account.account_number}/status",
        json={"status": "Active"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == ACCOUNT_ACTIVE

    db.expire_all()
    reloaded = db.get(Account, frozen_account.id)
    assert reloaded.status == ACCOUNT_ACTIVE


def test_unfreeze_via_convenience_endpoint(client, db, frozen_account):
    act_as(ROLE_ADMIN, user_id=1)

    response = client.post(f"/accounts/{frozen_account.account_number}/unfreeze")
    assert response.status_code == 200
    assert response.json()["status"] == ACCOUNT_ACTIVE


def test_active_account_cannot_be_unfrozen_again(client, db, active_account):
    act_as(ROLE_ADMIN, user_id=1)
    response = client.patch(
        f"/accounts/{active_account.account_number}/status",
        json={"status": "Active"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_STATUS_TRANSITION"


def test_unfreeze_rejected_for_unauthorized_roles(client, db, frozen_account):
    act_as(ROLE_TELLER, user_id=2)
    assert client.patch(
        f"/accounts/{frozen_account.account_number}/status", json={"status": "Active"}
    ).status_code == 403

    act_as(ROLE_CUSTOMER, user_id=3)
    assert client.patch(
        f"/accounts/{frozen_account.account_number}/status", json={"status": "Active"}
    ).status_code == 403


# ==================== C. CLOSE ====================

def test_admin_closes_account_with_zero_balance(client, db, zero_balance_account):
    act_as(ROLE_ADMIN, user_id=1)

    response = client.patch(
        f"/accounts/{zero_balance_account.account_number}/status",
        json={"status": "Closed"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == ACCOUNT_CLOSED

    db.expire_all()
    reloaded = db.get(Account, zero_balance_account.id)
    assert reloaded.status == ACCOUNT_CLOSED


def test_close_via_convenience_endpoint(client, db, zero_balance_account):
    act_as(ROLE_ADMIN, user_id=1)

    response = client.post(f"/accounts/{zero_balance_account.account_number}/close")
    assert response.status_code == 200
    assert response.json()["status"] == ACCOUNT_CLOSED


def test_close_rejected_when_balance_is_positive(client, db, active_account):
    act_as(ROLE_ADMIN, user_id=1)

    response = client.patch(
        f"/accounts/{active_account.account_number}/status",
        json={"status": "Closed"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "CANNOT_CLOSE_NONZERO_BALANCE"
    assert "Current balance is 5000.00" in response.json()["message"]


def test_close_rejected_when_balance_is_negative(client, db, sample_customer):
    act_as(ROLE_ADMIN, user_id=1)

    neg_account = Account(
        account_number="1000000096",
        customer_id=sample_customer.id,
        type=ACCOUNT_SAVINGS,
        balance=Decimal("-50.00"),
        status=ACCOUNT_ACTIVE,
    )
    db.add(neg_account)
    db.commit()

    response = client.patch(
        f"/accounts/{neg_account.account_number}/status",
        json={"status": "Closed"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "CANNOT_CLOSE_NONZERO_BALANCE"


def test_closed_account_cannot_be_reopened_or_modified(client, db, zero_balance_account):
    act_as(ROLE_ADMIN, user_id=1)

    # First close it
    client.patch(
        f"/accounts/{zero_balance_account.account_number}/status",
        json={"status": "Closed"},
    )

    # Attempt to unfreeze / reactivate
    res_activate = client.patch(
        f"/accounts/{zero_balance_account.account_number}/status",
        json={"status": "Active"},
    )
    assert res_activate.status_code == 400
    assert res_activate.json()["code"] == "ACCOUNT_ALREADY_CLOSED"

    # Attempt to freeze
    res_freeze = client.patch(
        f"/accounts/{zero_balance_account.account_number}/status",
        json={"status": "Frozen"},
    )
    assert res_freeze.status_code == 400
    assert res_freeze.json()["code"] == "ACCOUNT_ALREADY_CLOSED"

    # Attempt to close again
    res_close = client.patch(
        f"/accounts/{zero_balance_account.account_number}/status",
        json={"status": "Closed"},
    )
    assert res_close.status_code == 400
    assert res_close.json()["code"] == "ACCOUNT_ALREADY_CLOSED"


# ==================== D. FROZEN TRANSACTION RESTRICTIONS ====================

def test_deposit_into_frozen_account_is_rejected(client, db, frozen_account):
    act_as(ROLE_TELLER, user_id=10)
    initial_balance = frozen_account.balance

    response = client.post(
        "/transactions/deposit",
        json={"accountId": frozen_account.account_number, "amount": "500.00"},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "ACCOUNT_NOT_ACTIVE"

    # Balance must not have changed
    db.expire_all()
    assert db.get(Account, frozen_account.id).balance == initial_balance


def test_withdrawal_from_frozen_account_is_rejected(client, db, frozen_account):
    act_as(ROLE_TELLER, user_id=10)
    initial_balance = frozen_account.balance

    response = client.post(
        "/transactions/withdraw",
        json={"accountId": frozen_account.account_number, "amount": "500.00"},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "ACCOUNT_NOT_ACTIVE"

    db.expire_all()
    assert db.get(Account, frozen_account.id).balance == initial_balance


def test_transfer_from_frozen_account_is_rejected(client, db, frozen_account, active_account):
    act_as(ROLE_CUSTOMER, user_id=7, customer_id=frozen_account.customer_id)
    initial_source_balance = frozen_account.balance
    initial_dest_balance = active_account.balance

    response = client.post(
        "/transactions/transfer",
        json={
            "fromAccount": frozen_account.account_number,
            "toAccount": active_account.account_number,
            "amount": "500.00",
        },
    )
    assert response.status_code == 409
    assert response.json()["code"] == "ACCOUNT_NOT_ACTIVE"

    db.expire_all()
    assert db.get(Account, frozen_account.id).balance == initial_source_balance
    assert db.get(Account, active_account.id).balance == initial_dest_balance


def test_transfer_to_frozen_account_is_rejected(client, db, active_account, frozen_account):
    act_as(ROLE_CUSTOMER, user_id=7, customer_id=active_account.customer_id)
    initial_source_balance = active_account.balance
    initial_dest_balance = frozen_account.balance

    response = client.post(
        "/transactions/transfer",
        json={
            "fromAccount": active_account.account_number,
            "toAccount": frozen_account.account_number,
            "amount": "500.00",
        },
    )
    assert response.status_code == 409
    assert response.json()["code"] == "ACCOUNT_NOT_ACTIVE"

    db.expire_all()
    assert db.get(Account, active_account.id).balance == initial_source_balance
    assert db.get(Account, frozen_account.id).balance == initial_dest_balance


# ==================== E. AUDIT LOGGING & ATOMICITY ====================

def test_successful_transitions_create_audit_records(client, db, active_account, zero_balance_account):
    admin_id = 99
    act_as(ROLE_ADMIN, user_id=admin_id)

    # 1. Freeze active account
    res_freeze = client.patch(
        f"/accounts/{active_account.account_number}/status",
        json={"status": "Frozen"},
    )
    assert res_freeze.status_code == 200

    audit_freeze = (
        db.query(AuditLog)
        .filter(AuditLog.action == "ACCOUNT_FREEZE", AuditLog.user_id == admin_id)
        .first()
    )
    assert audit_freeze is not None
    assert audit_freeze.outcome == "SUCCESS"
    assert audit_freeze.timestamp is not None
    assert active_account.account_number in audit_freeze.details
    assert "status changed from Active to Frozen" in audit_freeze.details

    # 2. Unfreeze
    res_unfreeze = client.patch(
        f"/accounts/{active_account.account_number}/status",
        json={"status": "Active"},
    )
    assert res_unfreeze.status_code == 200

    audit_unfreeze = (
        db.query(AuditLog)
        .filter(AuditLog.action == "ACCOUNT_UNFREEZE", AuditLog.user_id == admin_id)
        .first()
    )
    assert audit_unfreeze is not None
    assert audit_unfreeze.outcome == "SUCCESS"
    assert "status changed from Frozen to Active" in audit_unfreeze.details

    # 3. Close zero-balance account
    res_close = client.patch(
        f"/accounts/{zero_balance_account.account_number}/status",
        json={"status": "Closed"},
    )
    assert res_close.status_code == 200

    audit_close = (
        db.query(AuditLog)
        .filter(AuditLog.action == "ACCOUNT_CLOSE", AuditLog.user_id == admin_id)
        .first()
    )
    assert audit_close is not None
    assert audit_close.outcome == "SUCCESS"
    assert "status changed from Active to Closed" in audit_close.details


def test_failed_transition_does_not_create_successful_audit_log(client, db, active_account):
    admin_id = 99
    act_as(ROLE_ADMIN, user_id=admin_id)

    # Attempt to close active account with non-zero balance (fails)
    response = client.patch(
        f"/accounts/{active_account.account_number}/status",
        json={"status": "Closed"},
    )
    assert response.status_code == 400

    # Verify no ACCOUNT_CLOSE record was written
    assert (
        db.query(AuditLog)
        .filter(AuditLog.action == "ACCOUNT_CLOSE")
        .count()
        == 0
    )


def test_atomic_rollback_on_audit_or_commit_failure(client, db, active_account):
    act_as(ROLE_ADMIN, user_id=1)

    with patch.object(db, "commit", side_effect=RuntimeError("DB Commit Crash")):
        with pytest.raises(RuntimeError):
            client.patch(
                f"/accounts/{active_account.account_number}/status",
                json={"status": "Frozen"},
            )

    # Account status must remain Active
    db.expire_all()
    assert db.get(Account, active_account.id).status == ACCOUNT_ACTIVE

    # No audit log entry
    assert (
        db.query(AuditLog)
        .filter(AuditLog.action == "ACCOUNT_FREEZE")
        .count()
        == 0
    )


# ==================== F. REQUEST VALIDATION ====================

def test_validation_rejects_conflicting_status_and_action(client, active_account):
    act_as(ROLE_ADMIN, user_id=1)
    response = client.patch(
        f"/accounts/{active_account.account_number}/status",
        json={"status": "Frozen", "action": "close"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert "Provide either 'status' or 'action', not both." in response.json()["message"]


def test_validation_rejects_missing_both_status_and_action(client, active_account):
    act_as(ROLE_ADMIN, user_id=1)
    response = client.patch(
        f"/accounts/{active_account.account_number}/status",
        json={},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert "Either 'status' or 'action' must be provided." in response.json()["message"]


def test_validation_rejects_explicit_null_status(client, active_account):
    act_as(ROLE_ADMIN, user_id=1)
    response = client.patch(
        f"/accounts/{active_account.account_number}/status",
        json={"status": None},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert "status cannot be null" in response.json()["message"]


def test_validation_rejects_explicit_null_action(client, active_account):
    act_as(ROLE_ADMIN, user_id=1)
    response = client.patch(
        f"/accounts/{active_account.account_number}/status",
        json={"action": None},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert "action cannot be null" in response.json()["message"]


def test_validation_rejects_invalid_status_value(client, active_account):
    act_as(ROLE_ADMIN, user_id=1)
    response = client.patch(
        f"/accounts/{active_account.account_number}/status",
        json={"status": "Destroy"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert "Invalid status or action 'Destroy'" in response.json()["message"]


def test_validation_rejects_whitespace_status(client, active_account):
    act_as(ROLE_ADMIN, user_id=1)
    response = client.patch(
        f"/accounts/{active_account.account_number}/status",
        json={"status": "   "},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


# ==================== G. ACCOUNT IDENTIFIER LOOKUP RULES ====================

def test_lookup_strictly_uses_account_number_for_10_digit_numeric(client, db, active_account):
    act_as(ROLE_ADMIN, user_id=1)
    # A 10-digit number that does not match any account_number returns 404
    # and does not fall back to checking primary key ID.
    non_existent_10_digit = "9999999999"
    response = client.patch(
        f"/accounts/{non_existent_10_digit}/status",
        json={"status": "Frozen"},
    )
    assert response.status_code == 404
    assert response.json()["code"] == "ACCOUNT_NOT_FOUND"

    from app.services.account_service import get_account_by_identifier
    assert get_account_by_identifier(db, "9999999999") is None


def test_lookup_by_short_numeric_id_uses_primary_key(client, db, active_account):
    from app.services.account_service import get_account_by_identifier
    # Shorter numeric identifier (length < 10) matches by PK ID
    found = get_account_by_identifier(db, active_account.id)
    assert found is not None
    assert found.id == active_account.id
    assert found.account_number == active_account.account_number

    # String representation of PK ID (e.g. "1")
    found_str = get_account_by_identifier(db, str(active_account.id))
    assert found_str is not None
    assert found_str.id == active_account.id


# ==================== H. CLOSED ACCOUNT TRANSACTION RESTRICTIONS ====================

def test_deposit_into_closed_account_is_rejected(client, db, closed_account):
    act_as(ROLE_TELLER, user_id=10)
    initial_balance = closed_account.balance

    response = client.post(
        "/transactions/deposit",
        json={"accountId": closed_account.account_number, "amount": "500.00"},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "ACCOUNT_NOT_ACTIVE"

    # Balance remains unchanged
    db.expire_all()
    assert db.get(Account, closed_account.id).balance == initial_balance


def test_withdrawal_from_closed_account_is_rejected(client, db, closed_account):
    act_as(ROLE_TELLER, user_id=10)
    initial_balance = closed_account.balance

    response = client.post(
        "/transactions/withdraw",
        json={"accountId": closed_account.account_number, "amount": "500.00"},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "ACCOUNT_NOT_ACTIVE"

    # Balance remains unchanged
    db.expire_all()
    assert db.get(Account, closed_account.id).balance == initial_balance


def test_transfer_from_closed_account_is_rejected(client, db, closed_account, active_account):
    act_as(ROLE_CUSTOMER, user_id=7, customer_id=closed_account.customer_id)
    initial_source_balance = closed_account.balance
    initial_dest_balance = active_account.balance

    response = client.post(
        "/transactions/transfer",
        json={
            "fromAccount": closed_account.account_number,
            "toAccount": active_account.account_number,
            "amount": "500.00",
        },
    )
    assert response.status_code == 409
    assert response.json()["code"] == "ACCOUNT_NOT_ACTIVE"

    # Balances remain unchanged
    db.expire_all()
    assert db.get(Account, closed_account.id).balance == initial_source_balance
    assert db.get(Account, active_account.id).balance == initial_dest_balance


def test_transfer_to_closed_account_is_rejected(client, db, active_account, closed_account):
    act_as(ROLE_CUSTOMER, user_id=7, customer_id=active_account.customer_id)
    initial_source_balance = active_account.balance
    initial_dest_balance = closed_account.balance

    response = client.post(
        "/transactions/transfer",
        json={
            "fromAccount": active_account.account_number,
            "toAccount": closed_account.account_number,
            "amount": "500.00",
        },
    )
    assert response.status_code == 409
    assert response.json()["code"] == "ACCOUNT_NOT_ACTIVE"

    # Balances remain unchanged
    db.expire_all()
    assert db.get(Account, active_account.id).balance == initial_source_balance
    assert db.get(Account, closed_account.id).balance == initial_dest_balance


# ==================== I. UNAUTHORIZED REQUEST AUDIT LOGGING ====================

def test_unauthorized_teller_status_update_logs_access_denied(client, db, active_account):
    act_as(ROLE_TELLER, user_id=22)
    response = client.patch(
        f"/accounts/{active_account.account_number}/status",
        json={"status": "Frozen"},
    )
    assert response.status_code == 403

    audit_entry = (
        db.query(AuditLog)
        .filter(AuditLog.action == "ACCESS_DENIED", AuditLog.user_id == 22)
        .first()
    )
    assert audit_entry is not None
    assert audit_entry.outcome == "DENIED"
    assert "Teller" in audit_entry.details
    assert "Admin" in audit_entry.details
    assert audit_entry.timestamp is not None


def test_unauthorized_customer_status_update_logs_access_denied(client, db, active_account):
    act_as(ROLE_CUSTOMER, user_id=33, customer_id=active_account.customer_id)
    response = client.patch(
        f"/accounts/{active_account.account_number}/status",
        json={"status": "Frozen"},
    )
    assert response.status_code == 403

    audit_entry = (
        db.query(AuditLog)
        .filter(AuditLog.action == "ACCESS_DENIED", AuditLog.user_id == 33)
        .first()
    )
    assert audit_entry is not None
    assert audit_entry.outcome == "DENIED"
    assert "Customer" in audit_entry.details
    assert "Admin" in audit_entry.details
    assert audit_entry.timestamp is not None


# ==================== J. CONCURRENCY SYNCHRONIZATION ====================

def test_update_account_status_uses_money_lock(client, db, active_account):
    from app.services import account_service
    act_as(ROLE_ADMIN, user_id=1)
    lock_entered = False

    orig_lock = account_service._money_lock
    class LockSpy:
        def __enter__(self):
            nonlocal lock_entered
            lock_entered = True
            return orig_lock.__enter__()

        def __exit__(self, exc_type, exc_val, exc_tb):
            return orig_lock.__exit__(exc_type, exc_val, exc_tb)

    with patch.object(account_service, "_money_lock", LockSpy()):
        response = client.patch(
            f"/accounts/{active_account.account_number}/status",
            json={"status": "Frozen"},
        )
        assert response.status_code == 200
        assert lock_entered is True
