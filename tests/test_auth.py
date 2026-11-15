
from datetime import datetime, timedelta, timezone
from fastapi import status
from sqlalchemy import event

from app.constants import USER_ACTIVE, USER_LOCKED
from app.models import AuditLog, User
from app.security import (
    hash_password,
    validate_password_complexity,
    validate_password_strength,
    verify_password,
)
from app.sessions import _sessions


def create_user(
    db,
    username="tarini",
    password="TestPass123!",
    role="Customer",
    user_status=USER_ACTIVE,
):
    user = User(
        username=username,
        password_hash=hash_password(password),
        role=role,
        status=user_status,
        failed_attempts=0,
        must_change_password=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login(client, username="tarini", password="TestPass123!"):
    return client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )


def test_login_success_returns_token_and_role(client, db):
    create_user(db)
    response = login(client)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["token"]
    assert data["role"] == "Customer"
    assert data["mustChangePassword"] is False


def test_login_wrong_password_returns_generic_error(client, db):
    create_user(db)
    response = login(client, password="WrongPassword!")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid username or password"


def test_login_unknown_username_returns_generic_error(client):
    response = login(client, username="unknown-user")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid username or password"


def test_locked_user_cannot_login(client, db):
    create_user(db, user_status=USER_LOCKED)
    response = login(client)

    assert response.status_code == status.HTTP_423_LOCKED


def test_account_locks_after_three_failed_attempts(client, db):
    user = create_user(db)

    for _ in range(3):
        response = login(client, password="WrongPassword!")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    db.refresh(user)
    assert user.failed_attempts == 3
    assert user.status == USER_LOCKED


def test_locked_account_rejects_correct_password(client, db):
    user = create_user(db)

    for _ in range(3):
        login(client, password="WrongPassword!")

    db.refresh(user)
    assert user.status == USER_LOCKED

    response = login(client, password="TestPass123!")
    assert response.status_code == status.HTTP_423_LOCKED


def test_successful_login_resets_failed_attempts(client, db):
    user = create_user(db)
    login(client, password="WrongPassword!")
    login(client, password="WrongPassword!")

    response = login(client)
    assert response.status_code == status.HTTP_200_OK

    db.refresh(user)
    assert user.failed_attempts == 0
    assert user.status == USER_ACTIVE


def test_lockout_creates_audit_event(client, db):
    user = create_user(db)

    for _ in range(3):
        login(client, password="WrongPassword!")

    events = (
        db.query(AuditLog)
        .filter(
            AuditLog.user_id == user.id,
            AuditLog.action == "ACCOUNT_LOCKOUT",
        )
        .all()
    )
    assert len(events) == 1
    assert events[0].outcome == "SUCCESS"


def test_logout_invalidates_session(client, db):
    create_user(db)
    response = login(client)
    assert response.status_code == status.HTTP_200_OK

    token = response.json()["token"]
    logout_response = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_response.status_code == status.HTTP_200_OK

    from app.routers.auth import _sessions
    assert token not in _sessions


def test_logout_without_token_is_rejected(client):
    response = client.post("/auth/logout")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_non_admin_cannot_unlock_account(client, db):
    create_user(db, username="tarini")
    create_user(
        db,
        username="locked-user",
        user_status=USER_LOCKED,
    )

    response = login(client)
    token = response.json()["token"]

    unlock_response = client.post(
        "/auth/unlock",
        json={"username": "locked-user"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert unlock_response.status_code == status.HTTP_403_FORBIDDEN


def test_admin_can_unlock_account(client, db):
    create_user(db, username="admin-user", role="Admin")
    locked_user = create_user(
        db,
        username="locked-user",
        user_status=USER_LOCKED,
    )
    locked_user.failed_attempts = 3
    db.commit()

    response = login(
        client,
        username="admin-user",
        password="TestPass123!",
    )
    token = response.json()["token"]

    unlock_response = client.post(
        "/auth/unlock",
        json={"username": "locked-user"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert unlock_response.status_code == status.HTTP_200_OK
    db.refresh(locked_user)
    assert locked_user.status == USER_ACTIVE
    assert locked_user.failed_attempts == 0


# ---------- US-04: Change Password and First-Login Password Reset (BMS-F-004, TC-Auth-03) ----------
def test_change_password_success(client, db):
    user = create_user(db, username="user-change-pwd", password="OldPassword1")
    login_resp = login(client, username="user-change-pwd", password="OldPassword1")
    token = login_resp.json()["token"]

    resp = client.post(
        "/auth/change-password",
        json={"currentPassword": "OldPassword1", "newPassword": "NewStrongPass1!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["message"] == "Password changed successfully"

    # Verify password hash updated in DB
    db.refresh(user)
    assert user.must_change_password is False

    # New password works for subsequent login
    new_login = login(client, username="user-change-pwd", password="NewStrongPass1!")
    assert new_login.status_code == status.HTTP_200_OK

    # Old password no longer works
    old_login = login(client, username="user-change-pwd", password="OldPassword1")
    assert old_login.status_code == status.HTTP_401_UNAUTHORIZED


def test_change_password_rejects_incorrect_current_password(client, db):
    create_user(db, username="user-wrong-current", password="OldPassword1")
    login_resp = login(client, username="user-wrong-current", password="OldPassword1")
    token = login_resp.json()["token"]

    resp = client.post(
        "/auth/change-password",
        json={"currentPassword": "IncorrectPassword999", "newPassword": "NewStrongPass1!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Incorrect current password" in resp.json()["message"]


def test_change_password_rejects_complexity_failures(client, db):
    create_user(db, username="user-complexity", password="OldPassword1")
    login_resp = login(client, username="user-complexity", password="OldPassword1")
    token = login_resp.json()["token"]

    # Shorter than 8 chars
    resp = client.post(
        "/auth/change-password",
        json={"currentPassword": "OldPassword1", "newPassword": "Ab1!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "at least 8 characters" in resp.json()["message"]

    # Missing uppercase
    resp = client.post(
        "/auth/change-password",
        json={"currentPassword": "OldPassword1", "newPassword": "lowercase123!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "uppercase" in resp.json()["message"]

    # Missing lowercase
    resp = client.post(
        "/auth/change-password",
        json={"currentPassword": "OldPassword1", "newPassword": "UPPERCASE123!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "lowercase" in resp.json()["message"]

    # Missing digit
    resp = client.post(
        "/auth/change-password",
        json={"currentPassword": "OldPassword1", "newPassword": "NoDigitsAllowed!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "digit" in resp.json()["message"]


def test_first_login_temporary_password_flow(client, db):
    # User created with must_change_password=True
    user = User(
        username="temp-user",
        password_hash=hash_password("TempPassword1!"),
        role="Customer",
        status=USER_ACTIVE,
        failed_attempts=0,
        must_change_password=True,
    )
    db.add(user)
    db.commit()

    login_resp = login(client, username="temp-user", password="TempPassword1!")
    assert login_resp.status_code == status.HTTP_200_OK
    assert login_resp.json()["mustChangePassword"] is True
    token = login_resp.json()["token"]

    # User cannot access protected endpoints requiring roles before changing password
    protected_resp = client.post(
        "/transactions/deposit",
        json={"accountId": "1000000001", "amount": "100.00"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert protected_resp.status_code == status.HTTP_403_FORBIDDEN
    assert "temporary password" in protected_resp.json()["message"]

    # Temporary-password user CAN access change-password endpoint
    change_resp = client.post(
        "/auth/change-password",
        json={"currentPassword": "TempPassword1!", "newPassword": "PermanentPass1!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert change_resp.status_code == status.HTTP_200_OK

    db.refresh(user)
    assert user.must_change_password is False

    # After changing password, subsequent login works with mustChangePassword=False
    relogin = login(client, username="temp-user", password="PermanentPass1!")
    assert relogin.status_code == status.HTTP_200_OK
    assert relogin.json()["mustChangePassword"] is False


def test_change_password_audit_logging_and_no_plaintext_passwords(client, db):
    user = create_user(db, username="audit-pwd-user", password="InitialPass1!")
    login_resp = login(client, username="audit-pwd-user", password="InitialPass1!")
    token = login_resp.json()["token"]

    # Failed attempt
    client.post(
        "/auth/change-password",
        json={"currentPassword": "WrongInitialPass!", "newPassword": "NewValidPass1!"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Successful attempt
    client.post(
        "/auth/change-password",
        json={"currentPassword": "InitialPass1!", "newPassword": "NewValidPass1!"},
        headers={"Authorization": f"Bearer {token}"},
    )

    audit_logs = db.query(AuditLog).filter(
        AuditLog.user_id == user.id,
        AuditLog.action == "CHANGE_PASSWORD",
    ).all()

    assert len(audit_logs) == 2
    outcomes = [log.outcome for log in audit_logs]
    assert "FAILURE" in outcomes
    assert "SUCCESS" in outcomes

    # Verify no plaintext passwords in any audit details
    for log in audit_logs:
        assert "InitialPass1!" not in (log.details or "")
        assert "WrongInitialPass!" not in (log.details or "")
        assert "NewValidPass1!" not in (log.details or "")


def test_change_password_atomicity_audit_failure_rolls_back(client, db):
    """If audit event storage fails during password change, the transaction must roll back:
    password hash unchanged, must_change_password preserved, and other sessions remain valid."""
    user = User(
        username="user-atomic-audit",
        password_hash=hash_password("OldPassword1!"),
        role="Customer",
        status=USER_ACTIVE,
        failed_attempts=0,
        must_change_password=True,
    )
    db.add(user)
    db.commit()

    token1 = "test-session-atomic-1"
    token2 = "test-session-atomic-2"
    _sessions[token1] = {
        "user_id": user.id,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    _sessions[token2] = {
        "user_id": user.id,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
    }

    def reject_change_password_audit(session, flush_context, instances):
        if any(isinstance(row, AuditLog) and row.action == "CHANGE_PASSWORD" and row.outcome == "SUCCESS" for row in session.new):
            raise RuntimeError("simulated audit database storage error")

    event.listen(db, "before_flush", reject_change_password_audit)
    try:
        resp = client.post(
            "/auth/change-password",
            json={"currentPassword": "OldPassword1!", "newPassword": "NewValidPass1!"},
            headers={"Authorization": f"Bearer {token1}"},
        )
    finally:
        event.remove(db, "before_flush", reject_change_password_audit)

    assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Failed to update password" in resp.json()["message"]

    # Verify atomicity in database:
    db.expire_all()
    user_after = db.query(User).filter_by(id=user.id).first()
    # Password hash was rolled back
    assert verify_password("OldPassword1!", user_after.password_hash) is True
    assert verify_password("NewValidPass1!", user_after.password_hash) is False
    # must_change_password flag was rolled back and preserved
    assert user_after.must_change_password is True

    # No successful audit log was committed
    success_audits = db.query(AuditLog).filter_by(
        user_id=user.id, action="CHANGE_PASSWORD", outcome="SUCCESS"
    ).all()
    assert len(success_audits) == 0

    # Sessions were NOT invalidated because transaction failed
    assert token1 in _sessions
    assert token2 in _sessions

    # Clean up test tokens
    _sessions.pop(token1, None)
    _sessions.pop(token2, None)


def test_change_password_invalidates_other_sessions_only_after_successful_commit(client, db):
    """Successful password change invalidates all other active sessions for that user,
    leaving only the current session active."""
    user = create_user(db, username="user-multi-session", password="OldPassword1!")
    token_current = "token-current-change"
    token_other_1 = "token-other-1"
    token_other_2 = "token-other-2"

    for tok in (token_current, token_other_1, token_other_2):
        _sessions[tok] = {
            "user_id": user.id,
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
        }

    resp = client.post(
        "/auth/change-password",
        json={"currentPassword": "OldPassword1!", "newPassword": "NewValidPass1!"},
        headers={"Authorization": f"Bearer {token_current}"},
    )
    assert resp.status_code == status.HTTP_200_OK

    # Current token remains active
    assert token_current in _sessions
    # Other tokens for this user are invalidated
    assert token_other_1 not in _sessions
    assert token_other_2 not in _sessions

    _sessions.pop(token_current, None)


def test_change_password_failed_attempts_do_not_invalidate_sessions(client, db):
    """Validation or password verification failures must not invalidate any user sessions."""
    user = create_user(db, username="user-failed-change", password="OldPassword1!")
    token_current = "token-fail-current"
    token_other = "token-fail-other"

    for tok in (token_current, token_other):
        _sessions[tok] = {
            "user_id": user.id,
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
        }

    # Wrong current password
    resp1 = client.post(
        "/auth/change-password",
        json={"currentPassword": "WrongCurrentPass1!", "newPassword": "NewValidPass1!"},
        headers={"Authorization": f"Bearer {token_current}"},
    )
    assert resp1.status_code == status.HTTP_400_BAD_REQUEST
    assert token_current in _sessions
    assert token_other in _sessions

    # Failing complexity
    resp2 = client.post(
        "/auth/change-password",
        json={"currentPassword": "OldPassword1!", "newPassword": "simple"},
        headers={"Authorization": f"Bearer {token_current}"},
    )
    assert resp2.status_code == status.HTTP_400_BAD_REQUEST
    assert token_current in _sessions
    assert token_other in _sessions

    _sessions.pop(token_current, None)
    _sessions.pop(token_other, None)


def test_change_password_accepts_valid_password_at_72_byte_limit(client, db):
    """bcrypt supports passwords up to 72 bytes. Exactly 72 UTF-8 bytes must succeed."""
    user = create_user(db, username="user-72-bytes", password="OldPassword1!")
    token = "token-72-bytes"
    _sessions[token] = {
        "user_id": user.id,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
    }

    # "Passw0rd!" is 9 bytes; adding 63 'A's gives exactly 72 bytes
    pwd_72 = "Passw0rd!" + "A" * 63
    assert len(pwd_72.encode("utf-8")) == 72

    resp = client.post(
        "/auth/change-password",
        json={"currentPassword": "OldPassword1!", "newPassword": pwd_72},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["message"] == "Password changed successfully"

    db.refresh(user)
    assert verify_password(pwd_72, user.password_hash) is True

    # Login works with the 72-byte password
    login_resp = login(client, username="user-72-bytes", password=pwd_72)
    assert login_resp.status_code == status.HTTP_200_OK

    _sessions.pop(token, None)


def test_change_password_rejects_80_byte_password_with_client_error(client, db):
    """Passwords exceeding 72 bytes must be rejected with HTTP 400 without crashing with 500.
    Must not modify stored hash or clear must_change_password."""
    user = User(
        username="user-80-bytes",
        password_hash=hash_password("OldPassword1!"),
        role="Customer",
        status=USER_ACTIVE,
        failed_attempts=0,
        must_change_password=True,
    )
    db.add(user)
    db.commit()
    token = "token-80-bytes"
    _sessions[token] = {
        "user_id": user.id,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
    }

    pwd_80 = "Passw0rd!" + "A" * 71
    assert len(pwd_80.encode("utf-8")) == 80

    resp = client.post(
        "/auth/change-password",
        json={"currentPassword": "OldPassword1!", "newPassword": pwd_80},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "72 bytes" in resp.json()["message"]

    # Verify stored hash and must_change_password are untouched
    db.refresh(user)
    assert verify_password("OldPassword1!", user.password_hash) is True
    assert user.must_change_password is True

    _sessions.pop(token, None)


def test_change_password_rejects_multibyte_password_exceeding_72_bytes(client, db):
    """Multibyte characters whose character count is < 72 but UTF-8 bytes > 72 must be rejected with HTTP 400."""
    user = create_user(db, username="user-multibyte-pwd", password="OldPassword1!")
    token = "token-multibyte"
    _sessions[token] = {
        "user_id": user.id,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
    }

    # "Passw0rd!" (9 bytes) + 25 '€' (each 3 bytes in UTF-8 = 75 bytes) = 84 UTF-8 bytes (34 characters total)
    multibyte_pwd = "Passw0rd!" + "€" * 25
    assert len(multibyte_pwd) == 34
    assert len(multibyte_pwd.encode("utf-8")) == 84

    resp = client.post(
        "/auth/change-password",
        json={"currentPassword": "OldPassword1!", "newPassword": multibyte_pwd},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "72 bytes" in resp.json()["message"]

    # Verify stored hash and state are untouched
    db.refresh(user)
    assert verify_password("OldPassword1!", user.password_hash) is True

    _sessions.pop(token, None)


def test_security_helpers_72_byte_boundary_handling():
    """Verify security helpers reject or handle >72 byte inputs gracefully without unhandled exceptions."""
    import pytest

    pwd_72 = "Passw0rd!" + "A" * 63
    pwd_80 = "Passw0rd!" + "A" * 71
    multibyte_84 = "Passw0rd!" + "€" * 25

    # validate_password_complexity
    ok, msg = validate_password_complexity(pwd_72)
    assert ok is True
    ok, msg = validate_password_complexity(pwd_80)
    assert ok is False and "72 bytes" in msg
    ok, msg = validate_password_complexity(multibyte_84)
    assert ok is False and "72 bytes" in msg

    # validate_password_strength
    assert validate_password_strength(pwd_72) is True
    assert validate_password_strength(pwd_80) is False
    assert validate_password_strength(multibyte_84) is False

    # hash_password raises ValueError with clear message instead of raw bcrypt crash
    with pytest.raises(ValueError, match="72 bytes"):
        hash_password(pwd_80)

    # verify_password safely returns False on >72 byte input without throwing exception
    hash_72 = hash_password(pwd_72)
    assert verify_password(pwd_72, hash_72) is True
    assert verify_password(pwd_80, hash_72) is False
    assert verify_password(multibyte_84, hash_72) is False
