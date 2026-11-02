"""Tests for US-10: Update Customer Details (BMS-F-011, TC-Acc-02).

Owner: Member 2 (Vijay).
"""

from datetime import date
from unittest.mock import patch

import pytest

from app.constants import ROLE_ADMIN, ROLE_CUSTOMER, ROLE_TELLER
from app.models import AuditLog, Customer
from tests.auth_helpers import act_as


@pytest.fixture()
def sample_customer(db):
    """Create a standard test customer."""
    customer = Customer(
        name="Sunita Sharma",
        date_of_birth=date(1991, 5, 12),
        address="10 Brigade Road, Bengaluru",
        phone="9876543210",
        email="sunita.sharma@example.com",
        id_proof_number="ID-PROOF-SUNITA-99",
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


# 1. Teller updates phone
def test_teller_updates_phone_successfully(client, db, sample_customer):
    act_as(ROLE_TELLER, user_id=101)

    response = client.put(
        f"/customers/{sample_customer.id}",
        json={"phone": "9123456780"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_customer.id
    assert data["phone"] == "9123456780"
    assert data["email"] == sample_customer.email
    assert data["address"] == sample_customer.address


# 2. Teller updates email
def test_teller_updates_email_successfully(client, db, sample_customer):
    act_as(ROLE_TELLER, user_id=101)

    response = client.put(
        f"/customers/{sample_customer.id}",
        json={"email": "sunita.new@example.com"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "sunita.new@example.com"


# 3. Teller updates address
def test_teller_updates_address_successfully(client, db, sample_customer):
    act_as(ROLE_TELLER, user_id=101)

    response = client.put(
        f"/customers/{sample_customer.id}",
        json={"address": "45 Lavelle Road, Bengaluru"},
    )

    assert response.status_code == 200
    assert response.json()["address"] == "45 Lavelle Road, Bengaluru"


# 4. Teller updates all contact fields together
def test_teller_updates_all_contact_fields_together(client, db, sample_customer):
    act_as(ROLE_TELLER, user_id=101)

    response = client.put(
        f"/customers/{sample_customer.id}",
        json={
            "phone": "+919876543219",
            "email": "sunita.complete@example.com",
            "address": "100 Residency Road, Bengaluru",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["phone"] == "+919876543219"
    assert data["email"] == "sunita.complete@example.com"
    assert data["address"] == "100 Residency Road, Bengaluru"


# 5. Invalid email format rejected
def test_invalid_email_format_rejected(client, db, sample_customer):
    act_as(ROLE_TELLER, user_id=101)

    response = client.put(
        f"/customers/{sample_customer.id}",
        json={"email": "not-an-email"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


# 6. Invalid phone format rejected
def test_invalid_phone_format_rejected(client, db, sample_customer):
    act_as(ROLE_TELLER, user_id=101)

    # Too short
    res_short = client.put(
        f"/customers/{sample_customer.id}",
        json={"phone": "12345"},
    )
    assert res_short.status_code == 400
    assert res_short.json()["code"] == "VALIDATION_ERROR"

    # Alphabetic
    res_alpha = client.put(
        f"/customers/{sample_customer.id}",
        json={"phone": "abcdefghij"},
    )
    assert res_alpha.status_code == 400
    assert res_alpha.json()["code"] == "VALIDATION_ERROR"


# 7. Whitespace-only address rejected
def test_whitespace_only_address_rejected(client, db, sample_customer):
    act_as(ROLE_TELLER, user_id=101)

    response = client.put(
        f"/customers/{sample_customer.id}",
        json={"address": "    "},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


# 8. Empty update request rejected
def test_empty_update_request_rejected(client, db, sample_customer):
    act_as(ROLE_TELLER, user_id=101)

    response = client.put(
        f"/customers/{sample_customer.id}",
        json={},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


# 8b. Explicit null values in mixed payloads rejected
def test_explicit_null_phone_in_mixed_payload_rejected(client, db, sample_customer):
    act_as(ROLE_TELLER, user_id=101)

    response = client.put(
        f"/customers/{sample_customer.id}",
        json={"phone": None, "email": "valid@example.com"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert "phone cannot be null" in response.json()["message"]


def test_explicit_null_email_in_mixed_payload_rejected(client, db, sample_customer):
    act_as(ROLE_TELLER, user_id=101)

    response = client.put(
        f"/customers/{sample_customer.id}",
        json={"email": None, "address": "123 Valid Street"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert "email cannot be null" in response.json()["message"]


def test_explicit_null_address_in_mixed_payload_rejected(client, db, sample_customer):
    act_as(ROLE_TELLER, user_id=101)

    response = client.put(
        f"/customers/{sample_customer.id}",
        json={"address": None, "phone": "9123456780"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert "address cannot be null" in response.json()["message"]


# 9. Nonexistent customer returns 404
def test_nonexistent_customer_returns_404(client, db):
    act_as(ROLE_TELLER, user_id=101)

    response = client.put(
        "/customers/999999",
        json={"phone": "9123456780"},
    )

    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "CUSTOMER_NOT_FOUND"


# 10. Unauthenticated access rejected
def test_unauthenticated_request_returns_401(client, db, sample_customer):
    # No act_as, so no Authorization header is set
    response = client.put(
        f"/customers/{sample_customer.id}",
        json={"phone": "9123456780"},
    )

    assert response.status_code == 401


# 11. Authenticated Customer forbidden
def test_customer_role_forbidden_returns_403(client, db, sample_customer):
    act_as(ROLE_CUSTOMER, user_id=5, customer_id=sample_customer.id)

    response = client.put(
        f"/customers/{sample_customer.id}",
        json={"phone": "9123456780"},
    )

    assert response.status_code == 403


# 12. Authenticated Admin forbidden (Teller-only action)
def test_admin_role_forbidden_returns_403(client, db, sample_customer):
    act_as(ROLE_ADMIN, user_id=1)

    response = client.put(
        f"/customers/{sample_customer.id}",
        json={"phone": "9123456780"},
    )

    assert response.status_code == 403


# 13. Audit record created with user, action, outcome, old and new values
def test_successful_update_creates_audit_log_with_old_and_new_values(
    client, db, sample_customer
):
    teller_user_id = 42
    act_as(ROLE_TELLER, user_id=teller_user_id)

    old_phone = sample_customer.phone
    new_phone = "9888877777"

    response = client.put(
        f"/customers/{sample_customer.id}",
        json={"phone": new_phone},
    )
    assert response.status_code == 200

    audit_entry = (
        db.query(AuditLog)
        .filter(
            AuditLog.action == "CUSTOMER_UPDATE",
            AuditLog.user_id == teller_user_id,
        )
        .first()
    )

    assert audit_entry is not None
    assert audit_entry.timestamp is not None
    assert audit_entry.outcome == "SUCCESS"
    assert str(sample_customer.id) in audit_entry.details
    assert f"phone: '{old_phone}' -> '{new_phone}'" in audit_entry.details


# 14. Sensitive data is not leaked into audit details
def test_audit_log_does_not_leak_sensitive_data(client, db, sample_customer):
    act_as(ROLE_TELLER, user_id=42)

    response = client.put(
        f"/customers/{sample_customer.id}",
        json={"address": "12 New Park View, Bengaluru"},
    )
    assert response.status_code == 200

    audit_entry = (
        db.query(AuditLog)
        .filter(AuditLog.action == "CUSTOMER_UPDATE")
        .order_by(AuditLog.id.desc())
        .first()
    )

    assert audit_entry is not None
    assert sample_customer.id_proof_number not in audit_entry.details
    assert "password" not in audit_entry.details.lower()
    assert "token" not in audit_entry.details.lower()


# 15. No audit log or DB write when values are unchanged
def test_no_audit_or_write_when_values_unchanged(client, db, sample_customer):
    act_as(ROLE_TELLER, user_id=42)

    audit_count_before = (
        db.query(AuditLog).filter(AuditLog.action == "CUSTOMER_UPDATE").count()
    )

    response = client.put(
        f"/customers/{sample_customer.id}",
        json={
            "phone": sample_customer.phone,
            "email": sample_customer.email,
            "address": sample_customer.address,
        },
    )
    assert response.status_code == 200

    audit_count_after = (
        db.query(AuditLog).filter(AuditLog.action == "CUSTOMER_UPDATE").count()
    )
    assert audit_count_after == audit_count_before


# 16. Database persistence verified in fresh query
def test_updated_details_persist_in_database(client, db, sample_customer):
    act_as(ROLE_TELLER, user_id=42)

    new_phone = "9777788888"
    new_email = "sunita.persisted@example.com"
    new_address = "99 Bannerghatta Road, Bengaluru"

    client.put(
        f"/customers/{sample_customer.id}",
        json={
            "phone": new_phone,
            "email": new_email,
            "address": new_address,
        },
    )

    # Clear session cache and query from scratch
    db.expire_all()
    fresh_customer = db.query(Customer).filter_by(id=sample_customer.id).one()

    assert fresh_customer.phone == new_phone
    assert fresh_customer.email == new_email
    assert fresh_customer.address == new_address


# 17. Atomic rollback when commit fails
def test_atomic_rollback_on_commit_failure(client, db, sample_customer):
    act_as(ROLE_TELLER, user_id=42)

    original_phone = sample_customer.phone

    # Simulate database commit error during customer update
    with patch.object(db, "commit", side_effect=RuntimeError("DB Commit Error")):
        with pytest.raises(RuntimeError):
            client.put(
                f"/customers/{sample_customer.id}",
                json={"phone": "9111122222"},
            )

    # Rollback must have reverted the customer in the database
    db.expire_all()
    reloaded_customer = db.query(Customer).filter_by(id=sample_customer.id).one()
    assert reloaded_customer.phone == original_phone

    # And no audit log must be written
    assert (
        db.query(AuditLog)
        .filter(AuditLog.action == "CUSTOMER_UPDATE")
        .count()
        == 0
    )
