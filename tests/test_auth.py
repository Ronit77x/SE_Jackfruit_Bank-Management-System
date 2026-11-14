
from fastapi import status

from app.constants import USER_ACTIVE, USER_LOCKED
from app.models import AuditLog, User
from app.security import hash_password


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
