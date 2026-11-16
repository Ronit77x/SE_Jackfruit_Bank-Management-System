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

def test_transfer_ui_served_at_ui_static_route_with_expected_assets(client):
    """GET /ui/transfer.html serves the new canonical page and loads expected CSS and JS assets."""
    from app.routers.accounts import STATIC_TRANSFER_HTML
    assert STATIC_TRANSFER_HTML.exists(), "Canonical app/static/transfer.html must exist"

    response = client.get("/ui/transfer.html")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")

    html = response.text
    # Canonical page content check
    assert html == STATIC_TRANSFER_HTML.read_text(encoding="utf-8")
    assert "Transfer Money" in html
    assert "fromAccountSelect" in html
    assert "toAccountInput" in html
    assert "amountInput" in html
    assert "btnReview" in html
    assert "btnConfirmSend" in html
    assert "executeTransfer" in html

    # Verify expected asset references exist in the canonical HTML
    assert '<link rel="stylesheet" href="/ui/css/style.css">' in html
    assert '<link rel="stylesheet" href="/ui/css/transfer.css">' in html
    assert '<script src="/ui/js/api.js"></script>' in html
    assert '<script src="/ui/js/transfer.js"></script>' in html

    # Verify that all referenced CSS and JS assets are successfully served
    assert client.get("/ui/css/style.css").status_code == 200
    assert client.get("/ui/css/transfer.css").status_code == 200
    assert client.get("/ui/js/api.js").status_code == 200
    assert client.get("/ui/js/transfer.js").status_code == 200


def test_transfer_and_alias_endpoints_serve_canonical_page_when_present(client):
    """GET /transfer and /transfer-ui serve the canonical static page when it exists."""
    from app.routers.accounts import FRONTEND_TRANSFER_HTML, STATIC_TRANSFER_HTML
    assert STATIC_TRANSFER_HTML.exists()
    assert FRONTEND_TRANSFER_HTML.exists()

    expected_canonical_content = STATIC_TRANSFER_HTML.read_text(encoding="utf-8")

    # 1. Primary route: GET /transfer
    res_transfer = client.get("/transfer")
    assert res_transfer.status_code == 200
    assert "text/html" in res_transfer.headers.get("content-type", "")
    assert res_transfer.text == expected_canonical_content
    assert "/ui/css/transfer.css" in res_transfer.text
    assert "/ui/js/transfer.js" in res_transfer.text

    # 2. Alias route: GET /transfer-ui
    res_alias = client.get("/transfer-ui")
    assert res_alias.status_code == 200
    assert "text/html" in res_alias.headers.get("content-type", "")
    assert res_alias.text == expected_canonical_content

    # Confirms it is serving the canonical page, distinct from the legacy file
    assert res_transfer.text != FRONTEND_TRANSFER_HTML.read_text(encoding="utf-8")


def test_transfer_endpoints_fallback_to_legacy_frontend_only_when_canonical_absent(client, monkeypatch):
    """GET /transfer and /transfer-ui fall back to frontend/transfer.html ONLY when canonical page is absent."""
    from app.routers.accounts import FRONTEND_TRANSFER_HTML
    assert FRONTEND_TRANSFER_HTML.exists(), "Legacy frontend/transfer.html fallback must exist"

    # Simulate canonical static file being absent
    monkeypatch.setattr(
        "app.routers.accounts.STATIC_TRANSFER_HTML",
        Path("non_existent_canonical_transfer.html"),
    )

    expected_legacy_content = FRONTEND_TRANSFER_HTML.read_text(encoding="utf-8")

    # Fallback works on /transfer
    res_transfer = client.get("/transfer")
    assert res_transfer.status_code == 200
    assert "text/html" in res_transfer.headers.get("content-type", "")
    assert res_transfer.text == expected_legacy_content

    # Fallback works on /transfer-ui
    res_alias = client.get("/transfer-ui")
    assert res_alias.status_code == 200
    assert res_alias.text == expected_legacy_content


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


def test_transfer_ui_fallback_if_both_files_missing(client, monkeypatch):
    """If both canonical and legacy transfer.html are missing, endpoint returns 404 cleanly instead of crashing."""
    monkeypatch.setattr(
        "app.routers.accounts.FRONTEND_TRANSFER_HTML",
        Path("non_existent_path_to_transfer.html"),
    )
    monkeypatch.setattr(
        "app.routers.accounts.STATIC_TRANSFER_HTML",
        Path("non_existent_path_to_transfer.html"),
    )
    res_transfer = client.get("/transfer")
    assert res_transfer.status_code == 404
    assert "Transfer UI not found" in res_transfer.text

    res_alias = client.get("/transfer-ui")
    assert res_alias.status_code == 404
    assert "Transfer UI not found" in res_alias.text


# ==================== E. LOGOUT & TC-UX-01 ALIGNMENT TESTS ====================

def test_transfer_ui_logout_invalidates_server_session_and_rejects_subsequent_access(client, db):
    """Calling POST /auth/logout removes session and subsequent /accounts/me calls return 401."""
    customer = Customer(
        name="Asha Rao",
        date_of_birth=date(1990, 3, 14),
        address="12 MG Road",
        phone="9000000001",
        email="asha@example.com",
        id_proof_number="ID-PROOF-LOGOUT-01",
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)

    user = User(
        username="asha_logout_user",
        password_hash=hash_password("Passw0rd!123"),
        role=ROLE_CUSTOMER,
        status="Active",
        customer_id=customer.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = "test_logout_flow_token"
    now = datetime.now(timezone.utc)
    _sessions[token] = {
        "user_id": user.id,
        "role": ROLE_CUSTOMER,
        "expires_at": now + timedelta(minutes=10),
        "last_activity": now,
    }

    try:
        # Access succeeds before logout
        res1 = client.get("/accounts/me", headers={"Authorization": f"Bearer {token}"})
        assert res1.status_code == 200

        # Perform backend logout
        res_logout = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert res_logout.status_code == 200
        assert res_logout.json() == {"message": "Logged out"}
        assert token not in _sessions

        # Subsequent access fails with 401
        res2 = client.get("/accounts/me", headers={"Authorization": f"Bearer {token}"})
        assert res2.status_code == 401
        assert "Invalid or expired session" in res2.text
    finally:
        _sessions.pop(token, None)


def test_transfer_ui_frontend_logout_and_tc_ux_01_script_contract():
    """Verify frontend/transfer.html contains required backend logout flow and corrected placeholder."""
    from app.routers.accounts import FRONTEND_TRANSFER_HTML
    assert FRONTEND_TRANSFER_HTML.exists()
    content = FRONTEND_TRANSFER_HTML.read_text(encoding="utf-8")

    # Verified logout implementation
    assert 'fetch("/auth/logout"' in content
    assert '"Authorization": `Bearer ${tokenToSend}`' in content
    assert 'sessionStorage.removeItem("bms_auth_token")' in content
    assert 'isLoggingOut' in content
    assert 'doLogout(true)' in content

    # Verified TC-UX-01 placeholder
    assert 'placeholder="Enter 10-digit account number (e.g. 1000000003)"' in content


def test_tc_ux_01_documentation_references_ravi_account_1000000003():
    """TC-UX-01 protocol must reference Customer 2 Ravi Kumar's account 1000000003."""
    doc_path = Path(__file__).resolve().parent.parent / "docs" / "test-plan" / "TC-UX-01-usability-test-protocol.md"
    assert doc_path.exists()
    text = doc_path.read_text(encoding="utf-8")

    assert "Customer 2 (**Ravi Kumar**, Account `1000000003`)" in text
    assert "recipient account number 1000000003" in text
    assert "Correct destination account (`1000000003`)" in text
    # Ensure obsolete Asha account number 1000000002 is not referenced as destination
    assert "recipient account number 1000000002" not in text

def test_transfer_ui_contract_excludes_ineligible_source_accounts():
    """transfer.html must exclude frozen, closed, and unknown-status accounts from the selector and explain why."""
    from app.routers.accounts import FRONTEND_TRANSFER_HTML
    assert FRONTEND_TRANSFER_HTML.exists()
    content = FRONTEND_TRANSFER_HTML.read_text(encoding="utf-8")

    # Safe status helper & filtering out non-active accounts
    assert 'function isEligibleStatus(status)' in content
    assert 'typeof status === "string" && status.trim().toLowerCase() === "active";' in content
    assert 'eligibleAccounts.forEach(acc => {' in content
    assert 'No eligible active accounts available' in content

    # Clear explanation using masked account numbers and safe fallback for unknown status
    assert 'acc.maskedAccountNumber || ""' in content
    assert '"Unknown status"' in content
    assert 'Excluded unavailable accounts:' in content
    assert 'No accounts can be used for transfers right now.' in content

    # Consistent helper reuse in display, amount validation, and review screen guard
    assert 'const isEligible = isEligibleStatus(acc.status);' in content
    assert 'if (!isEligibleStatus(acc.status))' in content
    assert 'if (!sourceAcc || !isEligibleStatus(sourceAcc.status))' in content
    assert 'Selected account is ${acc.status || "unavailable"} and cannot perform transfers.' in content


def test_canonical_transfer_ui_contract_excludes_ineligible_source_accounts():
    """Canonical app/static/transfer.html and transfer.js must exclude and disable non-active accounts."""
    from app.routers.accounts import STATIC_TRANSFER_HTML
    assert STATIC_TRANSFER_HTML.exists()

    static_dir = STATIC_TRANSFER_HTML.parent
    transfer_js_path = static_dir / "js" / "transfer.js"
    assert transfer_js_path.exists()
    js_content = transfer_js_path.read_text(encoding="utf-8")

    assert "function isEligibleStatus(status)" in js_content
    assert 'status.trim().toLowerCase() === "active"' in js_content
    assert "eligibleAccounts" in js_content
    assert "ineligibleAccounts" in js_content
    assert "No eligible active accounts available" in js_content
    assert "Excluded unavailable accounts:" in js_content
    assert "No accounts can be used for transfers right now." in js_content
    assert "opt.disabled = true" in js_content


def test_backend_transfer_validation_rejects_frozen_source_account(client, db, sample_data):
    """Backend must reject transfer attempts from a Frozen source account with 409."""
    a1 = sample_data["a1"]
    a3 = sample_data["a3"]
    a1.status = ACCOUNT_FROZEN
    db.commit()

    act_as(ROLE_CUSTOMER, user_id=1, customer_id=sample_data["c1"].id)
    response = client.post(
        "/transactions/transfer",
        json={
            "fromAccount": a1.account_number,
            "toAccount": a3.account_number,
            "amount": "500.00",
        },
    )
    assert response.status_code == 409
    assert response.json()["code"] == "ACCOUNT_NOT_ACTIVE"

    # Balances must be untouched
    db.refresh(a1)
    db.refresh(a3)
    assert a1.balance == Decimal("10000.00")
    assert a3.balance == Decimal("5000.00")


def test_backend_transfer_validation_rejects_closed_source_account(client, db, sample_data):
    """Backend must reject transfer attempts from a Closed source account with 409."""
    a1 = sample_data["a1"]
    a3 = sample_data["a3"]
    a1.status = ACCOUNT_CLOSED
    db.commit()

    act_as(ROLE_CUSTOMER, user_id=1, customer_id=sample_data["c1"].id)
    response = client.post(
        "/transactions/transfer",
        json={
            "fromAccount": a1.account_number,
            "toAccount": a3.account_number,
            "amount": "500.00",
        },
    )
    assert response.status_code == 409
    assert response.json()["code"] == "ACCOUNT_NOT_ACTIVE"

    db.refresh(a1)
    db.refresh(a3)
    assert a1.balance == Decimal("10000.00")
    assert a3.balance == Decimal("5000.00")


def test_backend_transfer_validation_rejects_closed_or_frozen_destination_account(client, db, sample_data):
    """Backend must reject transfer attempts to Frozen or Closed destination accounts with 409."""
    a1 = sample_data["a1"]
    a3 = sample_data["a3"]
    act_as(ROLE_CUSTOMER, user_id=1, customer_id=sample_data["c1"].id)

    # 1. Closed destination
    a3.status = ACCOUNT_CLOSED
    db.commit()
    res_closed = client.post(
        "/transactions/transfer",
        json={"fromAccount": a1.account_number, "toAccount": a3.account_number, "amount": "500.00"},
    )
    assert res_closed.status_code == 409
    assert res_closed.json()["code"] == "ACCOUNT_NOT_ACTIVE"

    # 2. Frozen destination
    a3.status = ACCOUNT_FROZEN
    db.commit()
    res_frozen = client.post(
        "/transactions/transfer",
        json={"fromAccount": a1.account_number, "toAccount": a3.account_number, "amount": "500.00"},
    )
    assert res_frozen.status_code == 409
    assert res_frozen.json()["code"] == "ACCOUNT_NOT_ACTIVE"

    db.refresh(a1)
    db.refresh(a3)
    assert a1.balance == Decimal("10000.00")


def test_backend_transfer_validation_enforces_business_rules_independent_of_frontend(client, db, sample_data):
    """Backend independently enforces ownership, self-transfer, daily limit, and minimum balance."""
    a1 = sample_data["a1"]
    a3 = sample_data["a3"]
    act_as(ROLE_CUSTOMER, user_id=1, customer_id=sample_data["c1"].id)

    # 1. Unowned source account -> 403 FORBIDDEN
    res_unowned = client.post(
        "/transactions/transfer",
        json={"fromAccount": a3.account_number, "toAccount": a1.account_number, "amount": "100.00"},
    )
    assert res_unowned.status_code == 403
    assert res_unowned.json()["code"] == "FORBIDDEN"

    # 2. Self transfer (same source and destination) -> 400 INVALID_TRANSFER
    res_same = client.post(
        "/transactions/transfer",
        json={"fromAccount": a1.account_number, "toAccount": a1.account_number, "amount": "100.00"},
    )
    assert res_same.status_code == 400
    assert res_same.json()["code"] == "INVALID_TRANSFER"

    # 3. Exceeds transfer limit (configured limit is 100,000.00) -> 422 TRANSFER_LIMIT_EXCEEDED
    # Fund source account with 200,000.00 so balance is completely sufficient (leaves 50,000 >= 1,000 min balance).
    # This guarantees that INSUFFICIENT_FUNDS cannot cause this test to pass accidentally.
    a1.balance = Decimal("200000.00")
    db.commit()

    res_limit = client.post(
        "/transactions/transfer",
        json={"fromAccount": a1.account_number, "toAccount": a3.account_number, "amount": "150000.00"},
    )
    assert res_limit.status_code == 422
    assert res_limit.json()["code"] == "TRANSFER_LIMIT_EXCEEDED"
    assert "Transfer limit of 100000 exceeded" in res_limit.json()["message"]

    # Restore a1 balance to 10,000.00 to keep subsequent minimum-balance tests isolated
    a1.balance = Decimal("10000.00")
    db.commit()

    # 4. Violates minimum balance (Savings requires 1,000 min balance; a1 has 10,000; transferring 9,500 leaves 500)
    res_min_bal = client.post(
        "/transactions/transfer",
        json={"fromAccount": a1.account_number, "toAccount": a3.account_number, "amount": "9500.00"},
    )
    assert res_min_bal.status_code == 422
    assert res_min_bal.json()["code"] == "INSUFFICIENT_FUNDS"

    # Ensure balances remain completely unchanged
    db.refresh(a1)
    db.refresh(a3)
    assert a1.balance == Decimal("10000.00")
    assert a3.balance == Decimal("5000.00")


def test_backend_transfer_validation_enforces_auth_roles_and_input_rules(client, db, sample_data):
    """Backend rejects unauthenticated, non-customer, temp-password, non-existent, and invalid-amount transfers."""
    a1 = sample_data["a1"]
    a3 = sample_data["a3"]

    # 1. Unauthenticated -> 401
    app_overrides_backup = dict(client.app.dependency_overrides)
    client.app.dependency_overrides.clear()
    try:
        res_unauth = client.post(
            "/transactions/transfer",
            json={"fromAccount": a1.account_number, "toAccount": a3.account_number, "amount": "100.00"},
        )
        assert res_unauth.status_code == 401
    finally:
        client.app.dependency_overrides.update(app_overrides_backup)

    # 2. Teller role -> 403
    act_as(ROLE_TELLER, user_id=2)
    res_teller = client.post(
        "/transactions/transfer",
        json={"fromAccount": a1.account_number, "toAccount": a3.account_number, "amount": "100.00"},
    )
    assert res_teller.status_code == 403

    # 3. Temporary password -> 403
    act_as(ROLE_CUSTOMER, user_id=1, customer_id=sample_data["c1"].id, must_change_password=True)
    res_temp = client.post(
        "/transactions/transfer",
        json={"fromAccount": a1.account_number, "toAccount": a3.account_number, "amount": "100.00"},
    )
    assert res_temp.status_code == 403

    # 4. Non-existent destination -> 404
    act_as(ROLE_CUSTOMER, user_id=1, customer_id=sample_data["c1"].id)
    res_not_found = client.post(
        "/transactions/transfer",
        json={"fromAccount": a1.account_number, "toAccount": "9999999999", "amount": "100.00"},
    )
    assert res_not_found.status_code == 404

    # 5. Zero or negative amount -> 400
    res_zero = client.post(
        "/transactions/transfer",
        json={"fromAccount": a1.account_number, "toAccount": a3.account_number, "amount": "0.00"},
    )
    assert res_zero.status_code == 400

    res_negative = client.post(
        "/transactions/transfer",
        json={"fromAccount": a1.account_number, "toAccount": a3.account_number, "amount": "-100.00"},
    )
    assert res_negative.status_code == 400

    # 6. More than 2 decimal places -> 400 VALIDATION_ERROR (Pydantic decimal_places constraint)
    res_precision = client.post(
        "/transactions/transfer",
        json={"fromAccount": a1.account_number, "toAccount": a3.account_number, "amount": "500.999"},
    )
    assert res_precision.status_code == 400
    assert res_precision.json()["code"] == "VALIDATION_ERROR"
    assert "decimal" in res_precision.json()["message"]

    # Ensure balances remain completely unchanged
    db.refresh(a1)
    db.refresh(a3)
    assert a1.balance == Decimal("10000.00")
    assert a3.balance == Decimal("5000.00")
