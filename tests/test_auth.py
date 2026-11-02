
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
