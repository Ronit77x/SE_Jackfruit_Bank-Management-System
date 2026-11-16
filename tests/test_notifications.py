from datetime import date, datetime, timezone

from app import crud
from app.constants import ROLE_ADMIN, ROLE_CUSTOMER, ROLE_TELLER
from tests.auth_helpers import act_as


def _customer(db, name):
    return crud.create_customer(
        db,
        name=name,
        date_of_birth=date(2000, 1, 1),
        address="1 Test Street",
        phone="9999999999",
        email=f"{name.lower()}@example.com",
        id_proof_number=f"ID-{name}",
    )


def test_customer_can_read_own_notifications_newest_first(client, db):
    customer = _customer(db, "Alice")
    older = crud.create_notification(db, customer.id, "Older notification")
    newer = crud.create_notification(db, customer.id, "Newer notification")
    act_as(ROLE_CUSTOMER, customer_id=customer.id)

    response = client.get("/notifications")

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == [newer.id, older.id]
    assert set(body[0]) == {"id", "message", "status", "created_at"}
    assert body[0]["message"] == "Newer notification"


def test_customer_only_sees_notifications_for_own_customer(client, db):
    customer_a = _customer(db, "Alice")
    customer_b = _customer(db, "Bob")
    own = crud.create_notification(db, customer_a.id, "A notification")
    other = crud.create_notification(db, customer_b.id, "B private notification")
    act_as(ROLE_CUSTOMER, customer_id=customer_a.id)

    response = client.get(f"/notifications?customer_id={customer_b.id}")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [own.id]
    assert other.message not in {item["message"] for item in response.json()}
    assert all("customer_id" not in item for item in response.json())


def test_missing_login_is_rejected(client):
    assert client.get("/notifications").status_code == 401


def test_teller_and_admin_are_rejected(client):
    act_as(ROLE_TELLER)
    assert client.get("/notifications").status_code == 403

    act_as(ROLE_ADMIN)
    assert client.get("/notifications").status_code == 403


def test_customer_without_customer_id_fails_safely(client):
    act_as(ROLE_CUSTOMER)

    response = client.get("/notifications")

    assert response.status_code == 403


def test_customer_with_no_notifications_gets_empty_list(client, db):
    customer = _customer(db, "Empty")
    act_as(ROLE_CUSTOMER, customer_id=customer.id)

    response = client.get("/notifications")

    assert response.status_code == 200
    assert response.json() == []


def test_notification_response_does_not_expose_internal_fields(client, db):
    customer = _customer(db, "Private")
    crud.create_notification(db, customer.id, "A private message")
    act_as(ROLE_CUSTOMER, customer_id=customer.id)

    response = client.get("/notifications")

    assert response.status_code == 200
    item = response.json()[0]
    assert set(item) == {"id", "message", "status", "created_at"}
    assert "password" not in item
    assert "password_hash" not in item
    assert "customer_id" not in item
