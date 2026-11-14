"""Account integration regressions for PRs #41 and #46."""
from decimal import Decimal

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import event

from app.models import Account, AuditLog, Customer, Transaction, User
from app.security import decrypt_value
from app.services import account_service
from tests.factories import create_account, create_user
from tests.test_accounts import new_customer_payload


@pytest.fixture(autouse=True)
def encryption_key(monkeypatch):
    monkeypatch.setenv("BMS_DATA_KEY", Fernet.generate_key().decode())


def login(client, user):
    response = client.post("/auth/login", json={
        "username": user.username, "password": "TestPassword123!",
    })
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()["token"]}


def teller_headers(client, db):
    return login(client, create_user(db, role="Teller"))


def test_open_account_with_real_teller_login_encrypts_id_and_audits_atomically(client, db):
    headers = teller_headers(client, db)
    response = client.post("/accounts", headers=headers, json=new_customer_payload())
    assert response.status_code == 201
    body = response.json()
    customer = db.get(Customer, body["customer_id"])
    assert customer.id_proof_number != "TEST-ID-001"
    assert decrypt_value(customer.id_proof_number) == "TEST-ID-001"
    audit = db.query(AuditLog).filter_by(action="ACCOUNT_OPENED").one()
    assert audit.user_id == db.query(User).filter_by(role="Teller").one().id
    assert audit.outcome == "SUCCESS" and audit.timestamp is not None
    assert body["account_number"] not in audit.details
    assert body["temporary_password"] not in audit.details
    assert "TEST-ID-001" not in audit.details
    assert db.query(Transaction).filter_by(account_id=body["account_id"]).one().amount == Decimal("1000")


def test_audit_write_failure_rolls_back_customer_account_login_and_deposit(client, db):
    headers = teller_headers(client, db)
    def reject_audit(session, flush_context, instances):
        if any(isinstance(row, AuditLog) and row.action == "ACCOUNT_OPENED" for row in session.new):
            raise RuntimeError("simulated audit storage failure")
    event.listen(db, "before_flush", reject_audit)
    try:
        response = client.post("/accounts", headers=headers, json=new_customer_payload())
    finally:
        event.remove(db, "before_flush", reject_audit)
    assert response.status_code == 500
    assert "simulated" not in response.text
    assert db.query(Customer).count() == 0
    assert db.query(Account).count() == 0
    assert db.query(Transaction).count() == 0
    assert db.query(User).filter_by(role="Customer").count() == 0
    assert db.query(AuditLog).filter_by(action="ACCOUNT_OPENED").count() == 0


def test_account_number_unique_constraint_collision_retries_without_losing_customer(client, db, monkeypatch):
    headers = teller_headers(client, db)
    existing = create_account(db, account_number="1000000001")
    candidates = iter([1, 2])
    monkeypatch.setattr(account_service.secrets, "randbelow", lambda _: next(candidates))
    response = client.post("/accounts", headers=headers, json=new_customer_payload())
    assert response.status_code == 201
    assert response.json()["account_number"] == "1000000002"
    assert db.query(Account).count() == 2
    assert db.query(Customer).count() == 2
    assert db.get(Account, existing.id).account_number == "1000000001"
    assert db.query(AuditLog).filter_by(action="ACCOUNT_OPENED").count() == 1


def test_exhausted_account_number_collisions_leave_no_partial_records(client, db, monkeypatch):
    headers = teller_headers(client, db)
    create_account(db, account_number="1000000001")
    monkeypatch.setattr(account_service.secrets, "randbelow", lambda _: 1)
    response = client.post("/accounts", headers=headers, json=new_customer_payload())
    assert response.status_code == 500
    assert db.query(Account).count() == 1
    assert db.query(Customer).count() == 1
    assert db.query(Transaction).count() == 0
    assert db.query(AuditLog).filter_by(action="ACCOUNT_OPENED").count() == 0


def test_missing_encryption_key_creates_no_partial_records(client, db, monkeypatch):
    headers = teller_headers(client, db)
    monkeypatch.delenv("BMS_DATA_KEY")
    response = client.post("/accounts", headers=headers, json=new_customer_payload())
    assert response.status_code == 500
    assert "BMS_DATA_KEY" not in response.text
    assert db.query(Customer).count() == db.query(Account).count() == 0
    assert db.query(Transaction).count() == 0


def test_open_account_rejects_missing_login_and_legacy_role_header(client, db):
    for headers in ({}, {"X-Test-Role": "Teller"}):
        response = client.post("/accounts", headers=headers, json=new_customer_payload())
        assert response.status_code == 401
    assert db.query(Account).count() == 0


@pytest.mark.parametrize("role", ["Customer", "Admin"])
def test_open_account_rejects_other_authenticated_roles(client, db, role):
    headers = login(client, create_user(db, role=role))
    response = client.post("/accounts", headers=headers, json=new_customer_payload())
    assert response.status_code == 403
    assert db.query(Account).count() == 0
    assert db.query(AuditLog).filter_by(action="ACCESS_DENIED").count() == 1


def test_existing_customer_audit_failure_does_not_leave_account_or_deposit(client, db):
    headers = teller_headers(client, db)
    existing = create_account(db)
    customer_id = existing.customer_id
    def reject_audit(session, flush_context, instances):
        if any(isinstance(row, AuditLog) and row.action == "ACCOUNT_OPENED" for row in session.new):
            raise RuntimeError("simulated audit storage failure")
    event.listen(db, "before_flush", reject_audit)
    try:
        response = client.post("/accounts", headers=headers, json={
            "customer_id": customer_id, "account_type": "Current", "deposit": "5000",
        })
    finally:
        event.remove(db, "before_flush", reject_audit)
    assert response.status_code == 500
    assert db.query(Account).count() == 1
    assert db.query(Customer).count() == 1
    assert db.query(Transaction).count() == 0
    assert db.query(AuditLog).filter_by(action="ACCOUNT_OPENED").count() == 0
