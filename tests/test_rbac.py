
from fastapi import status

from app.constants import USER_ACTIVE
from app.models import User
from app.security import hash_password
from app.deps import require_roles


def create_user(db, username, role):
    user = User(
        username=username,
        password_hash=hash_password("TestPass123!"),
        role=role,
        status=USER_ACTIVE,
        failed_attempts=0,
        must_change_password=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_customer_is_denied_admin_access(client, db):
    create_user(db, "customer-rbac", "Customer")
    response = client.post(
        "/auth/login",
        json={"username": "customer-rbac", "password": "TestPass123!"},
    )
    assert response.status_code == status.HTTP_200_OK
    token = response.json()["token"]

    response = client.post(
        "/auth/unlock",
        json={"username": "some-user"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_admin_can_access_admin_unlock(client, db):
    create_user(db, "admin-rbac", "Admin")
    create_user(db, "locked-rbac", "Customer")

    locked_user = db.query(User).filter_by(username="locked-rbac").first()
    locked_user.status = "Locked"
    db.commit()

    response = client.post(
        "/auth/login",
        json={"username": "admin-rbac", "password": "TestPass123!"},
    )
    assert response.status_code == status.HTTP_200_OK
    token = response.json()["token"]

    response = client.post(
        "/auth/unlock",
        json={"username": "locked-rbac"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK
