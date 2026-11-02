"""Tests for US-13: Search Customer / Account (BMS-F-014, TC-Acc-05).

Owner: Member 2 (Vijay).
"""

from datetime import date
from decimal import Decimal
import time

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
)
from app.models import Account, Customer
from app.services.customer_search_service import mask_account_number
from tests.auth_helpers import act_as


@pytest.fixture()
def populated_db(db):
    """Seed synthetic customers with various account types and phone formats."""
    # c1: Customer with 2 accounts and unformatted phone
    c1 = Customer(
        name="Deepa Sharma",
        date_of_birth=date(1990, 5, 15),
        address="12 MG Road, Bengaluru",
        phone="9876543210",
        email="deepa@example.com",
        id_proof_number="ID-PROOF-DEEPA-01",
    )
    # c2: Customer with 1 account and formatted phone (+91 with hyphens)
    c2 = Customer(
        name="Sunita Sharma",
        date_of_birth=date(1985, 3, 20),
        address="45 Brigade Road, Bengaluru",
        phone="+91-98765-43211",
        email="sunita@example.com",
        id_proof_number="ID-PROOF-SUNITA-02",
    )
    # c3: Customer with 1 account and spaced phone
    c3 = Customer(
        name="Ravi Kumar",
        date_of_birth=date(1992, 11, 8),
        address="8 Marine Drive, Kochi",
        phone="+91 91234 56789",
        email="ravi@example.com",
        id_proof_number="ID-PROOF-RAVI-03",
    )
    # c4: Customer with 0 accounts and 0-prefixed phone
    c4 = Customer(
        name="Amitabh Bachchan",
        date_of_birth=date(1942, 10, 11),
        address="Jalsa, Juhu, Mumbai",
        phone="09988776655",
        email="amitabh@example.com",
        id_proof_number="ID-PROOF-AMITABH-04",
    )
    # c5: Customer with literal special characters
    c5 = Customer(
        name="Special %_ Literal",
        date_of_birth=date(1999, 1, 1),
        address="Tech Park, Hyderabad",
        phone="9000000099",
        email="special@example.com",
        id_proof_number="ID-PROOF-SPECIAL-05",
    )

    db.add_all([c1, c2, c3, c4, c5])
    db.commit()

    # Accounts
    a1 = Account(
        account_number="1000000001",
        customer_id=c1.id,
        type=ACCOUNT_SAVINGS,
        balance=Decimal("5000.00"),
        status=ACCOUNT_ACTIVE,
    )
    a2 = Account(
        account_number="1000000002",
        customer_id=c1.id,
        type=ACCOUNT_CURRENT,
        balance=Decimal("12500.50"),
        status=ACCOUNT_ACTIVE,
    )
    a3 = Account(
        account_number="1000000003",
        customer_id=c2.id,
        type=ACCOUNT_SAVINGS,
        balance=Decimal("2000.00"),
        status=ACCOUNT_FROZEN,
    )
    a4 = Account(
        account_number="1000000004",
        customer_id=c3.id,
        type=ACCOUNT_SAVINGS,
        balance=Decimal("0.00"),
        status=ACCOUNT_CLOSED,
    )
    a5 = Account(
        account_number="1000000005",
        customer_id=c5.id,
        type=ACCOUNT_CURRENT,
        balance=Decimal("150.75"),
        status=ACCOUNT_ACTIVE,
    )

    db.add_all([a1, a2, a3, a4, a5])
    db.commit()

    return {
        "c1": c1,
        "c2": c2,
        "c3": c3,
        "c4": c4,
        "c5": c5,
        "a1": a1,
        "a2": a2,
        "a3": a3,
        "a4": a4,
        "a5": a5,
    }


# ==================== A. NAME SEARCH ====================

def test_search_by_full_name(client, populated_db):
    act_as(ROLE_TELLER, user_id=10)
    response = client.get("/customers?q=Deepa Sharma")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Deepa Sharma"
    assert data[0]["phone"] == "9876543210"
    assert data[0]["email"] == "deepa@example.com"
    # By name search, all associated accounts are returned
    assert len(data[0]["accounts"]) == 2


def test_search_by_partial_name(client, populated_db):
    act_as(ROLE_TELLER, user_id=10)
    response = client.get("/customers?q=eep")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Deepa Sharma"


def test_search_name_case_insensitive(client, populated_db):
    act_as(ROLE_TELLER, user_id=10)
    response = client.get("/customers?q=dEePa sHaRmA")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Deepa Sharma"


def test_search_multiple_customers_with_similar_names(client, populated_db):
    act_as(ROLE_TELLER, user_id=10)
    response = client.get("/customers?q=Sharma")
    assert response.status_code == 200
    data = response.json()
    names = [c["name"] for c in data]
    assert "Deepa Sharma" in names
    assert "Sunita Sharma" in names
    assert len(data) == 2


# ==================== B. PHONE NUMBER SEARCH (FORMATTED & NORMALIZED) ====================

def test_search_by_exact_unformatted_phone(client, populated_db):
    act_as(ROLE_TELLER, user_id=10)
    response = client.get("/customers?q=9876543210")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Deepa Sharma"
    # Phone search returns all associated accounts
    assert len(data[0]["accounts"]) == 2


def test_search_unformatted_query_matches_formatted_stored_phone(client, populated_db):
    act_as(ROLE_TELLER, user_id=10)
    # Stored: '+91-98765-43211', Query: '9876543211'
    response = client.get("/customers?q=9876543211")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Sunita Sharma"


def test_search_formatted_query_matches_unformatted_stored_phone(client, populated_db):
    act_as(ROLE_TELLER, user_id=10)
    # Stored: '9876543210', Query: '+91 98765 43210'
    response = client.get("/customers?q=%2B91%2098765%2043210")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Deepa Sharma"


def test_search_hyphenated_query_matches_unformatted_stored_phone(client, populated_db):
    act_as(ROLE_TELLER, user_id=10)
    # Stored: '9876543210', Query: '987-654-3210'
    response = client.get("/customers?q=987-654-3210")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Deepa Sharma"


def test_search_period_separated_query_matches_unformatted_stored_phone(client, populated_db):
    """Defensive correction 1: ALLOWED_PHONE_CHARS and SQL normalization both support periods."""
    act_as(ROLE_TELLER, user_id=10)
    # Stored: '9876543210', Query: '987.654.3210'
    response = client.get("/customers?q=987.654.3210")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Deepa Sharma"


def test_search_period_separated_stored_phone(client, db):
    """Defensive correction 1: Stored phone with periods matches normalized queries."""
    act_as(ROLE_TELLER, user_id=10)
    cust = Customer(
        name="Dot Phone User",
        date_of_birth=date(1993, 4, 12),
        address="Sector 14, Gurgaon",
        phone="987.654.9999",
        email="dot@example.com",
        id_proof_number="ID-DOT-PHONE-01",
    )
    db.add(cust)
    db.commit()

    # Match unformatted
    res_unformatted = client.get("/customers?q=9876549999")
    assert res_unformatted.status_code == 200
    assert res_unformatted.json()[0]["name"] == "Dot Phone User"

    # Match period query
    res_period = client.get("/customers?q=987.654.9999")
    assert res_period.status_code == 200
    assert res_period.json()[0]["name"] == "Dot Phone User"

    # Match country-code prefix with periods
    res_prefix = client.get("/customers?q=%2B91.987.654.9999")
    assert res_prefix.status_code == 200
    assert res_prefix.json()[0]["name"] == "Dot Phone User"


def test_search_zero_prefixed_query_and_stored_phone(client, populated_db):
    act_as(ROLE_TELLER, user_id=10)
    # Stored: '09988776655', Query: '9988776655'
    response = client.get("/customers?q=9988776655")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Amitabh Bachchan"

    # Query with leading 0 matches unformatted stored
    response2 = client.get("/customers?q=09876543210")
    assert response2.status_code == 200
    assert response2.json()[0]["name"] == "Deepa Sharma"


def test_search_phone_avoids_partial_matching(client, populated_db):
    act_as(ROLE_TELLER, user_id=10)
    # A short sequence of digits must NOT match 9876543210
    response = client.get("/customers?q=9876")
    assert response.status_code == 404
    assert response.json()["code"] == "CUSTOMER_NOT_FOUND"


def test_search_phone_avoids_matching_query_with_letters(client, populated_db):
    act_as(ROLE_TELLER, user_id=10)
    # Query with non-phone characters should not match phone
    response = client.get("/customers?q=9876543210abc")
    assert response.status_code == 404
    assert response.json()["code"] == "CUSTOMER_NOT_FOUND"


# ==================== C. ACCOUNT NUMBER SEARCH & RESULT SCOPE ====================

def test_search_by_account_number_returns_only_matching_account(client, populated_db):
    """Task 5: When searching by a specific account number, return that matching account

    rather than exposing all other accounts owned by that customer.
    """
    act_as(ROLE_TELLER, user_id=10)
    # Deepa Sharma owns 1000000001 (Savings) and 1000000002 (Current).
    # Searching for 1000000001 must return ONLY 1000000001 in her accounts list.
    response = client.get("/customers?q=1000000001")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Deepa Sharma"

    # Only 1 matching account is returned!
    accounts = data[0]["accounts"]
    assert len(accounts) == 1
    assert accounts[0]["accountNumber"] == "******0001"
    assert accounts[0]["type"] == ACCOUNT_SAVINGS

    # Account 1000000002 must NOT be in the results
    assert "0002" not in response.text


def test_search_by_second_account_number_returns_only_that_account(client, populated_db):
    """Task 5: Searching for the second account returns only the second account."""
    act_as(ROLE_TELLER, user_id=10)
    response = client.get("/customers?q=1000000002")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Deepa Sharma"

    accounts = data[0]["accounts"]
    assert len(accounts) == 1
    assert accounts[0]["accountNumber"] == "******0002"
    assert accounts[0]["type"] == ACCOUNT_CURRENT

    # Account 1000000001 must NOT be in the results
    assert "0001" not in response.text


def test_name_and_phone_search_returns_all_associated_accounts(client, populated_db):
    """Task 5: Name and phone searches return all customer accounts."""
    act_as(ROLE_TELLER, user_id=10)

    # Name search
    res_name = client.get("/customers?q=Deepa")
    assert res_name.status_code == 200
    assert len(res_name.json()[0]["accounts"]) == 2

    # Phone search
    res_phone = client.get("/customers?q=9876543210")
    assert res_phone.status_code == 200
    assert len(res_phone.json()[0]["accounts"]) == 2


# ==================== D. MASKING & SENSITIVE DATA ====================

def test_mask_account_number_valid_and_malformed_values():
    """Defensive correction: mask_account_number only accepts 10 digits and fails safely for malformed inputs."""
    # 1. Valid 10-digit numbers: exactly 6 stars + last 4 digits
    assert mask_account_number("1000000001") == "******0001"
    assert mask_account_number("1000001234") == "******1234"
    assert mask_account_number("9876543210") == "******3210"

    # 2. Short values (< 10 characters): fully masked with 10 asterisks without revealing any digits
    assert mask_account_number("1234") == "**********"
    assert mask_account_number("123") == "**********"
    assert mask_account_number("12") == "**********"
    assert mask_account_number("1") == "**********"
    assert mask_account_number("123456789") == "**********"
    assert "1234" not in mask_account_number("1234")
    assert "123" not in mask_account_number("123")

    # 3. Longer values (> 10 characters): fully masked with 10 asterisks without revealing any characters
    assert mask_account_number("123456789012") == "**********"
    assert "9012" not in mask_account_number("123456789012")

    # 4. Values containing letters, internal spaces, or special characters: fully masked
    assert mask_account_number("100000000A") == "**********"
    assert mask_account_number("ACC1000001") == "**********"
    assert mask_account_number("1000 00001") == "**********"
    assert mask_account_number("1000-00001") == "**********"
    assert mask_account_number("100000000!") == "**********"

    # 5. Empty / whitespace / None: return empty string
    assert mask_account_number("") == ""
    assert mask_account_number("   ") == ""
    assert mask_account_number(None) == ""


def test_account_numbers_are_masked_in_all_results(client, populated_db):
    act_as(ROLE_TELLER, user_id=10)
    response = client.get("/customers?q=Deepa")
    assert response.status_code == 200
    data = response.json()

    # Never expose full account numbers anywhere in the response text
    assert "1000000001" not in response.text
    assert "1000000002" not in response.text

    accounts = data[0]["accounts"]
    assert accounts[0]["accountNumber"] == "******0001"
    assert accounts[1]["accountNumber"] == "******0002"


def test_sensitive_personal_data_not_exposed(client, populated_db):
    act_as(ROLE_TELLER, user_id=10)
    response = client.get("/customers?q=Deepa")
    assert response.status_code == 200
    cust = response.json()[0]

    # Verify sensitive fields are omitted
    assert "date_of_birth" not in cust
    assert "dob" not in cust
    assert "address" not in cust
    assert "id_proof_number" not in cust
    assert "password" not in response.text
    assert "password_hash" not in response.text


def test_simplified_response_schema_no_duplicate_keys(client, populated_db):
    """Task 4: Confirm simplified schema with clean single naming convention."""
    act_as(ROLE_TELLER, user_id=10)
    response = client.get("/customers?q=Deepa")
    assert response.status_code == 200
    cust = response.json()[0]

    # Verify no duplicate snake_case/camelCase keys on customer
    assert "id" in cust
    assert "customerId" not in cust
    assert "customer_id" not in cust
    assert "name" in cust
    assert "phone" in cust
    assert "email" in cust
    assert "accounts" in cust

    # Verify clean account keys
    acc = cust["accounts"][0]
    assert "accountNumber" in acc
    assert "account_number" not in acc


def test_monetary_precision_preserved(client, populated_db):
    act_as(ROLE_TELLER, user_id=10)
    response = client.get("/customers?q=Deepa")
    assert response.status_code == 200
    accounts = response.json()[0]["accounts"]
    balances = [Decimal(str(a["balance"])) for a in accounts]
    assert Decimal("5000.00") in balances
    assert Decimal("12500.50") in balances


# ==================== E. ACCOUNT EDGES (ZERO ACCOUNTS, ETC) ====================

def test_customer_with_no_accounts_returns_empty_accounts_list(client, populated_db):
    act_as(ROLE_TELLER, user_id=10)
    response = client.get("/customers?q=Amitabh")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Amitabh Bachchan"
    assert data[0]["accounts"] == []


def test_customer_with_frozen_and_closed_accounts(client, populated_db):
    act_as(ROLE_TELLER, user_id=10)
    # Sunita has a Frozen account
    res_frozen = client.get("/customers?q=Sunita")
    assert res_frozen.status_code == 200
    assert res_frozen.json()[0]["accounts"][0]["status"] == ACCOUNT_FROZEN

    # Ravi has a Closed account
    res_closed = client.get("/customers?q=Ravi")
    assert res_closed.status_code == 200
    assert res_closed.json()[0]["accounts"][0]["status"] == ACCOUNT_CLOSED


# ==================== F. INPUT VALIDATION & ERROR HANDLING ====================

def test_search_rejects_empty_query_string(client, populated_db):
    act_as(ROLE_TELLER, user_id=10)
    response = client.get("/customers?q=")
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_SEARCH_QUERY"
    assert "empty or whitespace" in response.json()["message"]


def test_search_rejects_missing_query_parameter(client, populated_db):
    act_as(ROLE_TELLER, user_id=10)
    response = client.get("/customers")
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_SEARCH_QUERY"


def test_search_rejects_whitespace_only_query(client, populated_db):
    act_as(ROLE_TELLER, user_id=10)
    response = client.get("/customers?q=%20%20%20")
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_SEARCH_QUERY"


def test_search_rejects_overly_long_query(client, populated_db):
    act_as(ROLE_TELLER, user_id=10)
    long_q = "A" * 105
    response = client.get(f"/customers?q={long_q}")
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_SEARCH_QUERY"
    assert "maximum 100 characters" in response.json()["message"]


def test_search_unmatched_query_returns_generic_secure_404_message(client, populated_db):
    """Task 2: In the no-results 404 response, do not echo the user's raw search query."""
    act_as(ROLE_TELLER, user_id=10)
    response = client.get("/customers?q=TotallyNonExistentPerson12345")
    assert response.status_code == 404
    assert response.json()["code"] == "CUSTOMER_NOT_FOUND"
    assert response.json()["message"] == "No customers found matching the supplied search criteria."
    # Ensure raw query was NOT echoed
    assert "TotallyNonExistentPerson12345" not in response.text


def test_search_unmatched_account_number_never_appears_in_error_response(client, populated_db):
    """Task 2: Ensure a full account number does not appear in the error response."""
    act_as(ROLE_TELLER, user_id=10)
    non_existent_account = "9999999999"
    response = client.get(f"/customers?q={non_existent_account}")
    assert response.status_code == 404
    assert response.json()["code"] == "CUSTOMER_NOT_FOUND"
    assert response.json()["message"] == "No customers found matching the supplied search criteria."
    # Full account number must never leak in error response
    assert non_existent_account not in response.text


def test_search_wildcard_escaping_prevents_wildcard_leakage(client, populated_db):
    act_as(ROLE_TELLER, user_id=10)
    # Query with literal % should only match the customer having '%' in their name
    response = client.get("/customers?q=%25")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Special %_ Literal"


# ==================== G. AUTHORIZATION & SECURITY ====================

def test_search_allowed_for_teller(client, populated_db):
    act_as(ROLE_TELLER, user_id=101)
    response = client.get("/customers?q=Deepa")
    assert response.status_code == 200


def test_search_forbidden_for_customer(client, populated_db):
    act_as(ROLE_CUSTOMER, user_id=202, customer_id=1)
    response = client.get("/customers?q=Deepa")
    assert response.status_code == 403


def test_search_forbidden_for_admin(client, populated_db):
    act_as(ROLE_ADMIN, user_id=303)
    response = client.get("/customers?q=Deepa")
    assert response.status_code == 403


def test_search_unauthenticated_returns_401(client, populated_db):
    response = client.get("/customers?q=Deepa")
    assert response.status_code == 401


def test_search_forbidden_when_temporary_password_needs_change(client, populated_db):
    act_as(ROLE_TELLER, user_id=404, must_change_password=True)
    response = client.get("/customers?q=Deepa")
    assert response.status_code == 403
    assert "temporary password" in response.text


# ==================== H. PERFORMANCE (< 2.0 SECONDS) ====================

def test_search_performance_under_two_seconds(client, db):
    """BMS-F-014 / TC-Acc-05: search response within 2 seconds.

    Tested against a synthetic dataset of 500 customers and 1,000 accounts.
    """
    act_as(ROLE_TELLER, user_id=1)

    # Populate synthetic dataset
    customers_to_add = [
        Customer(
            name=f"Synthetic Customer {i:04d}",
            date_of_birth=date(1990, 1, 1),
            address=f"Synthetic Address {i}",
            phone=f"90000{i:05d}",
            email=f"synth_{i}@example.com",
            id_proof_number=f"ID-SYNTH-{i:06d}",
        )
        for i in range(1, 501)
    ]
    db.add_all(customers_to_add)
    db.commit()

    accounts_to_add = []
    for i, cust in enumerate(customers_to_add, start=1):
        accounts_to_add.append(
            Account(
                account_number=f"20000{i:05d}",
                customer_id=cust.id,
                type=ACCOUNT_SAVINGS,
                balance=Decimal("1000.00"),
                status=ACCOUNT_ACTIVE,
            )
        )
        accounts_to_add.append(
            Account(
                account_number=f"30000{i:05d}",
                customer_id=cust.id,
                type=ACCOUNT_CURRENT,
                balance=Decimal("2500.00"),
                status=ACCOUNT_ACTIVE,
            )
        )
    db.add_all(accounts_to_add)
    db.commit()

    # Benchmark search queries
    queries = [
        ("name_partial", "Customer 025"),
        ("phone_exact", "9000000250"),
        ("account_exact", "2000000250"),
        ("name_multiple", "Synthetic Customer 01"),
    ]

    for label, query in queries:
        start_time = time.perf_counter()
        response = client.get(f"/customers?q={query}")
        duration = time.perf_counter() - start_time

        assert response.status_code == 200, f"Query '{query}' failed"
        assert duration < 2.0, f"Query '{query}' took {duration:.4f}s, expected < 2.0s"
        print(f"\n[PERFORMANCE] Query '{query}' ({label}) executed in {duration * 1000:.2f} ms")
