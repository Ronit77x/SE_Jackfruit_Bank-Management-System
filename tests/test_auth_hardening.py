"""Hardening of login, lockout and role checks (BMS-F-001, BMS-F-002, BMS-F-003, BMS-SR-003, BMS-SR-004, BMS-SR-006).

These tests complement tests/test_auth.py and tests/test_rbac.py.
"""
import threading
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import crud
from app.constants import ACCOUNT_SAVINGS, ROLE_ADMIN, ROLE_CUSTOMER, ROLE_TELLER, USER_ACTIVE, USER_INACTIVE, USER_LOCKED
from app.database import Base, get_db
from app.main import app
from app.models import AuditLog, User
from app.security import hash_password
from app.sessions import _sessions
from tests.test_crud import _customer

PASSWORD = "Passw0rd!"


@pytest.fixture(scope="module")
def password_hash():
    return hash_password(PASSWORD)


def login(client, username, password=PASSWORD):
    return client.post("/auth/login", json={"username": username, "password": password})


def token_for(client, username):
    return login(client, username).json()["token"]


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def account_for(db):
    return crud.create_account(db, _customer(db).id, ACCOUNT_SAVINGS, Decimal("10000"))


# ---------- lockout ----------
def test_parallel_wrong_passwords_still_lock_the_account(tmp_path, password_hash):
    """12 guesses sent at the same moment must count as 12 failures, not as 1."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'login.db'}", connect_args={"check_same_thread": False, "timeout": 20}
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with factory() as setup:
        crud.create_user(setup, "victim", password_hash, ROLE_CUSTOMER)

    def override():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override
    try:
        client = TestClient(app)
        threads = [threading.Thread(target=login, args=(client, "victim", "Wrong-guess-1")) for _ in range(12)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        with factory() as check:
            user = check.query(User).filter_by(username="victim").one()
            assert user.status == USER_LOCKED
            assert user.failed_attempts >= 3
        # and the right password is now rejected as well
        assert login(client, "victim").status_code == 423
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_locked_status_is_only_revealed_with_the_right_password(client, db, password_hash):
    user = crud.create_user(db, "locked1", password_hash, ROLE_TELLER)
    crud.update_user(db, user.id, status=USER_LOCKED)
    assert login(client, "locked1", "wrong-password").status_code == 401  # looks like any wrong password
    assert login(client, "locked1").status_code == 423


def test_inactive_and_unknown_users_look_the_same(client, db, password_hash):
    user = crud.create_user(db, "gone1", password_hash, ROLE_TELLER)
    crud.update_user(db, user.id, status=USER_INACTIVE)
    inactive = login(client, "gone1")
    unknown = login(client, "nobody-here")
    assert inactive.status_code == unknown.status_code == 401
    assert inactive.json()["message"] == unknown.json()["message"]


def test_failed_logins_never_store_the_password(client, db, password_hash):
    crud.create_user(db, "teller1", password_hash, ROLE_TELLER)
    login(client, "teller1", "SuperSecret-123")
    assert db.query(AuditLog).count() >= 1
    assert all("SuperSecret-123" not in row.details for row in db.query(AuditLog))


# ---------- role checks ----------
def test_wrong_role_gets_403_and_an_audit_event(client, db, password_hash):
    account = account_for(db)
    crud.create_user(db, "teller1", password_hash, ROLE_TELLER)
    token = token_for(client, "teller1")
    response = client.post(
        "/transactions/transfer",
        headers=bearer(token),
        json={"fromAccount": account.account_number, "toAccount": "1000000099", "amount": "10"},
    )
    assert response.status_code == 403
    denied = db.query(AuditLog).filter_by(action="ACCESS_DENIED", outcome="DENIED").all()
    assert len(denied) == 1


def test_missing_and_unknown_tokens_get_401(client, db):
    account = account_for(db)
    body = {"accountId": account.account_number, "amount": "10"}
    assert client.post("/transactions/deposit", json=body).status_code == 401
    assert client.post("/transactions/deposit", json=body, headers=bearer("not-a-token")).status_code == 401


def test_the_old_test_role_header_grants_nothing(client, db):
    account = account_for(db)
    response = client.post(
        "/transactions/deposit",
        json={"accountId": account.account_number, "amount": "10"},
        headers={"X-Test-Role": "Teller"},
    )
    assert response.status_code == 401


def test_teller_can_deposit_with_a_real_login(client, db, password_hash):
    account = account_for(db)
    crud.create_user(db, "teller1", password_hash, ROLE_TELLER)
    response = client.post(
        "/transactions/deposit",
        headers=bearer(token_for(client, "teller1")),
        json={"accountId": account.account_number, "amount": "250"},
    )
    assert response.status_code == 201
    db.refresh(account)
    assert account.balance == Decimal("10250.00")


def test_user_with_temporary_password_cannot_use_other_endpoints(client, db, password_hash):
    account = account_for(db)
    crud.create_user(db, "teller9", password_hash, ROLE_TELLER, must_change_password=True)
    response = client.post(
        "/transactions/deposit",
        headers=bearer(token_for(client, "teller9")),
        json={"accountId": account.account_number, "amount": "10"},
    )
    assert response.status_code == 403
    assert "temporary password" in response.json()["message"]


# ---------- sessions (BMS-SR-003) ----------
def test_session_expires_after_ten_minutes_without_use(client, db, password_hash):
    account = account_for(db)
    crud.create_user(db, "teller1", password_hash, ROLE_TELLER)
    token = token_for(client, "teller1")
    body = {"accountId": account.account_number, "amount": "10"}
    assert client.post("/transactions/deposit", json=body, headers=bearer(token)).status_code == 201

    _sessions[token]["last_activity"] = datetime.now(timezone.utc) - timedelta(minutes=11)
    _sessions[token]["expires_at"] = datetime.now(timezone.utc) + timedelta(minutes=5)
    assert client.post("/transactions/deposit", json=body, headers=bearer(token)).status_code == 401


def test_logout_ends_the_session(client, db, password_hash):
    crud.create_user(db, "teller1", password_hash, ROLE_TELLER)
    token = token_for(client, "teller1")
    assert client.post("/auth/logout", headers=bearer(token)).status_code == 200
    account = account_for(db)
    response = client.post(
        "/transactions/deposit",
        headers=bearer(token),
        json={"accountId": account.account_number, "amount": "10"},
    )
    assert response.status_code == 401


# ---------- admin unlock ----------
def test_only_an_admin_can_unlock_and_login_works_again(client, db, password_hash):
    crud.create_user(db, "admin1", password_hash, ROLE_ADMIN)
    crud.create_user(db, "teller1", password_hash, ROLE_TELLER)
    victim = crud.create_user(db, "teller2", password_hash, ROLE_TELLER)
    crud.update_user(db, victim.id, status=USER_LOCKED, failed_attempts=3)

    teller_token = token_for(client, "teller1")
    assert client.post("/auth/unlock", headers=bearer(teller_token), json={"username": "teller2"}).status_code == 403

    admin_token = token_for(client, "admin1")
    assert client.post("/auth/unlock", headers=bearer(admin_token), json={"username": "teller2"}).status_code == 200
    assert login(client, "teller2").status_code == 200
    assert db.query(AuditLog).filter_by(action="ACCOUNT_UNLOCK").count() == 1


# ---------- error format ----------
def test_errors_keep_the_standard_fields_and_the_fastapi_detail_field(client):
    response = client.post("/auth/login", json={"username": "x", "password": "wrong"})
    body = response.json()
    assert {"code", "message", "timestamp", "traceId", "detail"} <= set(body)
    assert body["detail"] == body["message"]
