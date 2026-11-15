"""Tests for Teller Accounts UI (US-08, US-10, US-13) and associated endpoints."""
import shutil
import subprocess
from decimal import Decimal
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from app.constants import ROLE_CUSTOMER, ROLE_TELLER
from app.models import Account, Customer, User
from tests.factories import create_customer, create_user
from tests.test_accounts import new_customer_payload

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def data_encryption_key(monkeypatch):
    monkeypatch.setenv("BMS_DATA_KEY", Fernet.generate_key().decode())


def login_user(client, user, password="TestPassword123!"):
    response = client.post(
        "/auth/login",
        json={"username": user.username, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_teller_accounts_page_is_served(client):
    response = client.get("/ui/teller-accounts.html")
    assert response.status_code == 200
    text = response.text

    # Viewport and branding
    assert 'name="viewport"' in text
    assert "Accounts" in text
    assert "/ui/css/style.css" in text
    assert "/ui/css/teller-accounts.css" in text
    assert "/ui/js/api.js" in text
    assert "/ui/js/teller-accounts.js" in text

    # Section 1: Search Customer & Account (US-13)
    assert 'id="search-form"' in text
    assert 'id="search-query"' in text
    assert 'id="search-submit"' in text
    assert 'id="search-clear"' in text
    assert 'id="search-results-wrap"' in text
    assert 'id="search-rows"' in text

    # Section 2: Open Bank Account (US-08)
    assert 'id="mode-new"' in text
    assert 'id="mode-existing"' in text
    assert 'id="new-customer-fields"' in text
    assert 'id="existing-customer-fields"' in text
    assert 'id="existing-customer-id"' in text
    assert 'id="new-customer-name"' in text
    assert 'id="new-customer-dob"' in text
    assert 'id="new-customer-address"' in text
    assert 'id="new-customer-phone"' in text
    assert 'id="new-customer-email"' in text
    assert 'id="new-customer-idproof"' in text
    assert 'id="open-account-type"' in text
    assert 'id="open-deposit"' in text
    assert 'id="open-account-submit"' in text
    assert 'id="open-account-success"' in text
    assert 'id="open-account-details-list"' in text
    assert 'id="temp-password-box"' in text
    assert 'id="temp-password-value"' in text
    assert 'id="open-account-dismiss"' in text

    # Section 3: Update Customer Contact Details (US-10)
    assert 'id="update-customer-form"' in text
    assert 'id="update-customer-id"' in text
    assert 'id="update-phone"' in text
    assert 'id="update-email"' in text
    assert 'id="update-address"' in text
    assert 'id="update-customer-submit"' in text
    assert 'id="update-customer-clear"' in text
    assert 'id="update-customer-success"' in text
    assert 'id="update-customer-details-list"' in text


def test_teller_accounts_assets_served(client):
    css_res = client.get("/ui/css/teller-accounts.css")
    assert css_res.status_code == 200
    assert "[hidden]" in css_res.text
    assert "display: none !important" in css_res.text

    js_res = client.get("/ui/js/teller-accounts.js")
    assert js_res.status_code == 200
    assert "bms.requireRole" in js_res.text
    assert 'bms.header("Accounts")' in js_res.text


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")
def test_teller_accounts_node_checks():
    result = subprocess.run(
        ["node", str(ROOT / "tests" / "ui" / "teller_accounts_check.js")],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_teller_open_account_new_customer_real_backend(client, db):
    teller = create_user(db, role=ROLE_TELLER)
    headers = login_user(client, teller)

    payload = new_customer_payload(account_type="Savings", deposit="1500.00")
    payload["phone"] = "9876543210"
    payload["email"] = "newcustomer@example.com"

    response = client.post("/accounts", headers=headers, json=payload)
    assert response.status_code == 201
    body = response.json()

    assert "customer_id" in body
    assert "account_id" in body
    assert "account_number" in body
    assert body["account_type"] == "Savings"
    assert Decimal(str(body["balance"])) == Decimal("1500.00")
    assert body["status"] == "Active"
    assert "temporary_password" in body
    temp_pw = body["temporary_password"]
    assert len(temp_pw) >= 8

    # Customer user was created and can authenticate with temporary password
    cust_user = db.query(User).filter_by(customer_id=body["customer_id"]).one()
    cust_login = client.post(
        "/auth/login",
        json={"username": cust_user.username, "password": temp_pw},
    )
    assert cust_login.status_code == 200
    cust_auth = cust_login.json()
    assert cust_auth["mustChangePassword"] is True
    assert cust_auth["role"] == "Customer"


def test_teller_open_account_existing_customer_real_backend(client, db):
    teller = create_user(db, role=ROLE_TELLER)
    headers = login_user(client, teller)

    # First open an initial account
    first_res = client.post("/accounts", headers=headers, json=new_customer_payload())
    assert first_res.status_code == 201
    first_body = first_res.json()
    cust_id = first_body["customer_id"]

    # Now open a second account (Current, min 5000) for the existing customer
    second_res = client.post(
        "/accounts",
        headers=headers,
        json={"customer_id": cust_id, "account_type": "Current", "deposit": "5000.00"},
    )
    assert second_res.status_code == 201
    second_body = second_res.json()

    assert second_body["customer_id"] == cust_id
    assert second_body["account_type"] == "Current"
    assert Decimal(str(second_body["balance"])) == Decimal("5000.00")
    # No temporary password for existing customer
    assert "temporary_password" not in second_body or second_body.get("temporary_password") is None


def test_non_teller_cannot_open_account(client, db):
    cust_user = create_user(db, role=ROLE_CUSTOMER)
    headers = login_user(client, cust_user)

    response = client.post("/accounts", headers=headers, json=new_customer_payload())
    assert response.status_code == 403


def test_teller_update_customer_contact_details_real_backend(client, db):
    teller = create_user(db, role=ROLE_TELLER)
    headers = login_user(client, teller)

    customer = create_customer(db, phone="9111111111", email="original@example.com", address="Original Address")

    response = client.put(
        f"/customers/{customer.id}",
        headers=headers,
        json={"phone": "9222222222", "email": "updated@example.com", "address": "New Address 123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == customer.id
    assert data["phone"] == "9222222222"
    assert data["email"] == "updated@example.com"
    assert data["address"] == "New Address 123"


def test_non_teller_cannot_update_customer_details(client, db):
    cust_user = create_user(db, role=ROLE_CUSTOMER)
    headers = login_user(client, cust_user)
    customer = create_customer(db)

    response = client.put(
        f"/customers/{customer.id}",
        headers=headers,
        json={"phone": "9333333333"},
    )
    assert response.status_code == 403


def test_teller_search_customers_and_accounts_real_backend(client, db):
    teller = create_user(db, role=ROLE_TELLER)
    headers = login_user(client, teller)

    # Open an account to have a searchable customer with an account
    open_res = client.post(
        "/accounts",
        headers=headers,
        json=new_customer_payload(account_type="Savings", deposit="1000.00"),
    )
    assert open_res.status_code == 201
    created_cust_id = open_res.json()["customer_id"]

    # Empty query returns 400 per US-13 API contract
    empty_res = client.get("/customers", headers=headers)
    assert empty_res.status_code == 400
    assert empty_res.json()["code"] == "INVALID_SEARCH_QUERY"

    # Search by customer name
    search_res = client.get("/customers?q=Test+Customer", headers=headers)
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert isinstance(search_data, list)
    matching = [c for c in search_data if c["id"] == created_cust_id]
    assert len(matching) == 1
    assert len(matching[0]["accounts"]) >= 1
    # Check that account number is masked
    acc = matching[0]["accounts"][0]
    assert "******" in acc["accountNumber"]

    # Search by 10-digit account number
    acc_num = open_res.json()["account_number"]
    acc_search = client.get(f"/customers?q={acc_num}", headers=headers)
    assert acc_search.status_code == 200
    acc_data = acc_search.json()
    assert len(acc_data) == 1
    assert acc_data[0]["id"] == created_cust_id

    # Search with no matching records returns 404 per US-13 API contract
    not_found = client.get("/customers?q=NonExistent99999", headers=headers)
    assert not_found.status_code == 404
    assert not_found.json()["code"] == "CUSTOMER_NOT_FOUND"


def test_non_teller_cannot_search_customers(client, db):
    cust_user = create_user(db, role=ROLE_CUSTOMER)
    headers = login_user(client, cust_user)

    response = client.get("/customers?q=anything", headers=headers)
    assert response.status_code == 403


def test_teller_open_account_deposit_below_minimum_rejected(client, db):
    teller = create_user(db, role=ROLE_TELLER)
    headers = login_user(client, teller)

    # Savings deposit below 1000
    res_sav = client.post(
        "/accounts",
        headers=headers,
        json=new_customer_payload(account_type="Savings", deposit="999.00"),
    )
    assert res_sav.status_code == 400

    # Current deposit below 5000
    res_cur = client.post(
        "/accounts",
        headers=headers,
        json=new_customer_payload(account_type="Current", deposit="4999.00"),
    )
    assert res_cur.status_code == 400


def test_teller_update_customer_explicit_null_rejected(client, db):
    teller = create_user(db, role=ROLE_TELLER)
    headers = login_user(client, teller)
    customer = create_customer(db)

    # Explicit null is rejected by Pydantic reject_explicit_null validator with 400 VALIDATION_ERROR
    response = client.put(
        f"/customers/{customer.id}",
        headers=headers,
        json={"phone": None, "email": "valid@example.com"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert "phone cannot be null" in response.json()["message"]
