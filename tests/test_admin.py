from app.constants import ROLE_TELLER, USER_ACTIVE, USER_INACTIVE, USER_LOCKED
from app.models import AuditLog, User
from app.security import verify_password


def test_admin_can_create_teller_with_hashed_password(client, db):
    response = client.post("/admin/users", json={"username": "teller1", "password": "initial-secret"})

    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "teller1"
    assert body["role"] == ROLE_TELLER
    assert "password" not in body
    assert "password_hash" not in body

    user = db.query(User).filter_by(username="teller1").one()
    assert user.password_hash != "initial-secret"
    assert verify_password("initial-secret", user.password_hash)
    assert db.query(AuditLog).one().action == "CREATE_TELLER"


def test_admin_can_deactivate_teller_and_audits_change(client, db):
    user = User(username="teller1", password_hash="hash", role=ROLE_TELLER, status=USER_ACTIVE)
    db.add(user)
    db.commit()

    response = client.patch(f"/admin/users/{user.id}", json={"action": "deactivate"})

    assert response.status_code == 200
    assert response.json()["status"] == USER_INACTIVE
    assert db.get(User, user.id).status == USER_INACTIVE
    audit = db.query(AuditLog).one()
    assert audit.action == "DEACTIVATE_TELLER"
    assert "hash" not in audit.details


def test_admin_can_unlock_teller_and_resets_failures(client, db):
    user = User(
        username="teller1", password_hash="hash", role=ROLE_TELLER,
        status=USER_LOCKED, failed_attempts=3,
    )
    db.add(user)
    db.commit()

    response = client.patch(f"/admin/users/{user.id}", json={"action": "unlock"})

    assert response.status_code == 200
    assert response.json()["status"] == USER_ACTIVE
    assert response.json()["failed_attempts"] == 0
    assert db.get(User, user.id).failed_attempts == 0
    assert db.query(AuditLog).one().action == "UNLOCK_TELLER"


def test_admin_rejects_invalid_action_and_missing_user_without_audit(client, db):
    user = User(username="teller1", password_hash="hash", role=ROLE_TELLER)
    db.add(user)
    db.commit()

    invalid = client.patch(f"/admin/users/{user.id}", json={"action": "delete"})
    missing = client.patch("/admin/users/9999", json={"action": "unlock"})

    assert invalid.status_code == 400
    assert missing.status_code == 404
    assert db.query(AuditLog).count() == 0


def test_admin_cannot_create_duplicate_username(client, db):
    db.add(User(username="teller1", password_hash="hash", role=ROLE_TELLER))
    db.commit()

    response = client.post("/admin/users", json={"username": "teller1", "password": "secret"})

    assert response.status_code == 409
    assert db.query(AuditLog).count() == 0
