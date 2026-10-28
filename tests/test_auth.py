
from fastapi import status

from app.constants import USER_ACTIVE, USER_LOCKED
from app.models import User
from app.security import hash_password


def create_user(db, username="tarini", password="TestPass123!", role="Customer", user_status=USER_ACTIVE):
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


def test_login_success_returns_token_and_role(client, db):
    create_user(db)

    response = client.post(
        "/auth/login",
        json={"username": "tarini", "password": "TestPass123!"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["token"]
    assert data["role"] == "Customer"
    assert data["mustChangePassword"] is False


def test_login_wrong_password_returns_generic_error(client, db):
    create_user(db)

    response = client.post(
        "/auth/login",
        json={"username": "tarini", "password": "WrongPassword!"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid username or password"


def test_login_unknown_username_returns_generic_error(client, db):
    response = client.post(
        "/auth/login",
        json={"username": "unknown-user", "password": "TestPass123!"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid username or password"


def test_locked_user_cannot_login(client, db):
    create_user(db, user_status=USER_LOCKED)

    response = client.post(
        "/auth/login",
        json={"username": "tarini", "password": "TestPass123!"},
    )

    assert response.status_code == status.HTTP_423_LOCKED



def test_logout_invalidates_session(client, db):
    create_user(db)

    login_response = client.post(
        "/auth/login",
        json={"username": "tarini", "password": "TestPass123!"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["token"]

    logout_response = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_response.status_code == 200

    from app.routers.auth import _sessions
    assert token not in _sessions


def test_logout_without_token_is_rejected(client):
    response = client.post("/auth/logout")
    assert response.status_code == 401
