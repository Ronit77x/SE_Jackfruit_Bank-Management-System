"""Tests for US-14: Usability of Fund Transfer Flow (BMS-NF-004, TC-UX-01).

Owner: Member 2 (Vijay).
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from app.constants import (
    ACCOUNT_ACTIVE,
    ACCOUNT_CLOSED,
    ACCOUNT_CURRENT,
    ACCOUNT_FROZEN,
    ACCOUNT_SAVINGS,
    ROLE_ADMIN,
    ROLE_CUSTOMER,
    ROLE_TELLER,
    USER_INACTIVE,
)
from app.models import Account, Customer, User
from app.security import hash_password
from app.sessions import _sessions
from tests.auth_helpers import act_as


@pytest.fixture()
def sample_data(db):
    """Seed test customers and accounts."""
    c1 = Customer(
        name="Asha Rao",
        date_of_birth=date(1990, 3, 14),
        address="12 MG Road, Bengaluru",
        phone="9000000001",
        email="asha@example.com",
        id_proof_number="ID-PROOF-ASHA-01",
    )
    c2 = Customer(
        name="Ravi Kumar",
        date_of_birth=date(1985, 7, 2),
        address="5 Anna Salai, Chennai",
        phone="9000000002",
        email="ravi@example.com",
        id_proof_number="ID-PROOF-RAVI-02",
    )
    c3_no_accounts = Customer(
        name="No Accounts Customer",
        date_of_birth=date(1995, 1, 1),
        address="Residency Road, Bengaluru",
        phone="9000000003",
        email="noacc@example.com",
        id_proof_number="ID-PROOF-NOACC-03",
    )
    db.add_all([c1, c2, c3_no_accounts])
    db.commit()

    # Customer 1 has 2 accounts
    a1 = Account(
        account_number="1000000001",
        customer_id=c1.id,
        type=ACCOUNT_SAVINGS,
        balance=Decimal("10000.00"),
        status=ACCOUNT_ACTIVE,
    )
    a2 = Account(
        account_number="1000000002",
        customer_id=c1.id,
        type=ACCOUNT_CURRENT,
        balance=Decimal("25000.50"),
        status=ACCOUNT_ACTIVE,
    )

    # Customer 2 has 1 account
    a3 = Account(
        account_number="1000000003",
        customer_id=c2.id,
        type=ACCOUNT_SAVINGS,
        balance=Decimal("5000.00"),
        status=ACCOUNT_ACTIVE,
    )

    db.add_all([a1, a2, a3])
    db.commit()

    return {
        "c1": c1,
        "c2": c2,
        "c3": c3_no_accounts,
        "a1": a1,
        "a2": a2,
        "a3": a3,
    }


# ==================== A. ACCOUNT RETRIEVAL FOR CUSTOMER ====================

def test_customer_can_retrieve_own_accounts(client, sample_data):
    """Customer retrieves only their own accounts via GET /accounts/me."""
    c1 = sample_data["c1"]
    act_as(ROLE_CUSTOMER, user_id=1, customer_id=c1.id)

    response = client.get("/accounts/me")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    # Check account numbers and balances
    acc_numbers = [item["accountNumber"] for item in data]
    assert "1000000001" in acc_numbers
    assert "1000000002" in acc_numbers
    # Customer 2's account must NOT be present
    assert "1000000003" not in acc_numbers

    # Verify masked format is included
    masked_numbers = [item["maskedAccountNumber"] for item in data]
    assert "******0001" in masked_numbers
    assert "******0002" in masked_numbers


def test_customer_can_retrieve_accounts_via_my_accounts_alias(client, sample_data):
    """Alias route GET /accounts/my-accounts works identically."""
    c1 = sample_data["c1"]
    act_as(ROLE_CUSTOMER, user_id=1, customer_id=c1.id)

    response = client.get("/accounts/my-accounts")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_customer_cannot_retrieve_another_customers_accounts(client, sample_data):
    """Customer 2 only receives their own single account, never Customer 1's accounts."""
    c2 = sample_data["c2"]
    act_as(ROLE_CUSTOMER, user_id=2, customer_id=c2.id)

    response = client.get("/accounts/me")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["accountNumber"] == "1000000003"
    assert "1000000001" not in response.text
    assert "1000000002" not in response.text


def test_customer_with_no_accounts_returns_empty_list(client, sample_data):
    """A customer with no accounts receives a clean 200 response with an empty list."""
    c3 = sample_data["c3"]
    act_as(ROLE_CUSTOMER, user_id=3, customer_id=c3.id)

    response = client.get("/accounts/me")
    assert response.status_code == 200
    assert response.json() == []


def test_user_without_customer_id_returns_empty_list(client):
    """An authenticated user object with no customer_id returns an empty list."""
    act_as(ROLE_CUSTOMER, user_id=99, customer_id=None)

    response = client.get("/accounts/me")
    assert response.status_code == 200
    assert response.json() == []


def test_only_necessary_fields_returned_no_sensitive_data(client, sample_data):
    """Response includes only id, accountNumber, maskedAccountNumber, type, status, balance."""
    c1 = sample_data["c1"]
    act_as(ROLE_CUSTOMER, user_id=1, customer_id=c1.id)

    response = client.get("/accounts/me")
    assert response.status_code == 200
    item = response.json()[0]

    assert "id" in item
    assert "accountNumber" in item
    assert "maskedAccountNumber" in item
    assert "type" in item
    assert "status" in item
    assert "balance" in item

    # Ensure sensitive customer fields are absent
    assert "date_of_birth" not in item
    assert "dob" not in item
    assert "address" not in item
    assert "id_proof_number" not in item
    assert "password" not in response.text
    assert "password_hash" not in response.text


# ==================== B. AUTHORIZATION & SECURITY ====================

def test_unauthenticated_request_rejected_with_401(client):
    """Unauthenticated access to /accounts/me is rejected."""
    response = client.get("/accounts/me")
    assert response.status_code == 401


def test_teller_role_cannot_access_customer_accounts(client):
    """Teller role cannot access customer accounts listing endpoint."""
    act_as(ROLE_TELLER, user_id=10)
    response = client.get("/accounts/me")
    assert response.status_code == 403


def test_admin_role_cannot_access_customer_accounts(client):
    """Admin role cannot access customer accounts listing endpoint."""
    act_as(ROLE_ADMIN, user_id=20)
    response = client.get("/accounts/me")
    assert response.status_code == 403


def test_user_with_temporary_password_cannot_access_accounts(client, sample_data):
    """User forced to change temporary password is blocked until password change (BMS-F-004)."""
    c1 = sample_data["c1"]
    act_as(ROLE_CUSTOMER, user_id=1, customer_id=c1.id, must_change_password=True)

    response = client.get("/accounts/me")
    assert response.status_code == 403
    assert "temporary password" in response.text


# ==================== C. WEB UI SERVING ====================

def test_transfer_ui_served_at_transfer_endpoint(client):
    """GET /transfer serves the HTML/CSS/JS customer transfer interface."""
    response = client.get("/transfer")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")

    # Check key UI structure elements
    html = response.text
    assert "Transfer Money" in html
    assert "fromAccountSelect" in html
    assert "toAccountInput" in html
    assert "amountInput" in html
    assert "btnReview" in html
    assert "btnConfirmSend" in html
    assert "executeTransfer" in html


def test_transfer_ui_served_at_alias_route(client):
    """GET /transfer-ui serves the same interface."""
    response = client.get("/transfer-ui")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Transfer Money" in response.text


# ==================== D. DEFENSIVE & EDGE CASE TESTS ====================

def test_accounts_me_missing_or_malformed_auth_header(client):
    """Ensure GET /accounts/me fails cleanly with 401 when auth header is missing or malformed."""
    # 1. Missing header
    res1 = client.get("/accounts/me")
    assert res1.status_code == 401
    assert "Authentication required" in res1.text

    # 2. Non-Bearer scheme
    res2 = client.get("/accounts/me", headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert res2.status_code == 401
    assert "Authentication required" in res2.text

    # 3. Non-existent / invalid session token
    res3 = client.get("/accounts/me", headers={"Authorization": "Bearer non_existent_token_12345"})
    assert res3.status_code == 401
    assert "Invalid or expired session" in res3.text


def test_accounts_me_rejects_inactive_user(client, db):
    """User marked Inactive cannot access /accounts/me even with an active session token."""
    inactive_user = User(
        username="inactive_customer",
        password_hash=hash_password("Passw0rd!123"),
        role=ROLE_CUSTOMER,
        status=USER_INACTIVE,
    )
    db.add(inactive_user)
    db.commit()
    db.refresh(inactive_user)

    token = "test_inactive_session_token"
    now = datetime.now(timezone.utc)
    _sessions[token] = {
        "user_id": inactive_user.id,
        "role": ROLE_CUSTOMER,
        "expires_at": now + timedelta(minutes=10),
        "last_activity": now,
    }

    try:
        response = client.get("/accounts/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
        assert "User is unavailable" in response.text
    finally:
        _sessions.pop(token, None)


def test_customer_accounts_with_frozen_and_closed_status(client, db, sample_data):
    """Accounts with Frozen and Closed statuses are returned accurately."""
    c1 = sample_data["c1"]
    frozen_acc = Account(
        account_number="1000000088",
        customer_id=c1.id,
        type=ACCOUNT_SAVINGS,
        balance=Decimal("2000.00"),
        status=ACCOUNT_FROZEN,
    )
    closed_acc = Account(
        account_number="1000000099",
        customer_id=c1.id,
        type=ACCOUNT_CURRENT,
        balance=Decimal("0.00"),
        status=ACCOUNT_CLOSED,
    )
    db.add_all([frozen_acc, closed_acc])
    db.commit()

    act_as(ROLE_CUSTOMER, user_id=1, customer_id=c1.id)
    response = client.get("/accounts/me")
    assert response.status_code == 200
    data = response.json()

    statuses = {item["accountNumber"]: item["status"] for item in data}
    assert statuses["1000000088"] == ACCOUNT_FROZEN
    assert statuses["1000000099"] == ACCOUNT_CLOSED


def test_transfer_ui_fallback_if_file_missing(client, monkeypatch):
    """If transfer.html is missing, endpoint returns 404 cleanly instead of crashing."""
    monkeypatch.setattr(
        "app.routers.accounts.FRONTEND_TRANSFER_HTML",
        Path("non_existent_path_to_transfer.html"),
    )
    response = client.get("/transfer")
    assert response.status_code == 404
    assert "Transfer UI not found" in response.text
