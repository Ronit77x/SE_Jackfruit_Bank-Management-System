from datetime import datetime, timezone

import pytest

from app import crud
from tests.auth_helpers import act_as


def add_log(db, user_id, action, timestamp):
    entry = crud.create_audit_log(db, user_id, action, "SUCCESS", "safe details")
    entry.timestamp = timestamp
    db.commit()
    return entry


def test_admin_can_list_audit_logs_newest_first(client, db):
    add_log(db, 10, "OLDER", datetime(2026, 1, 1, tzinfo=timezone.utc))
    add_log(db, 11, "NEWER", datetime(2026, 1, 2, tzinfo=timezone.utc))
    act_as("Admin")

    response = client.get("/admin/audit-logs")

    assert response.status_code == 200
    assert [row["action"] for row in response.json()] == ["NEWER", "OLDER"]
    assert set(response.json()[0]) == {"id", "timestamp", "user_id", "action", "outcome", "details"}


@pytest.mark.parametrize("role", ["Customer", "Teller"])
def test_only_admin_can_list_audit_logs(client, role):
    act_as(role)
    assert client.get("/admin/audit-logs").status_code == 403


def test_unauthenticated_audit_log_access_is_rejected(client):
    assert client.get("/admin/audit-logs").status_code == 401


def test_audit_filters_and_ist_date_boundaries(client, db):
    # 00:00 IST is the preceding UTC day at 18:30.
    add_log(db, 7, "DEPOSIT", datetime(2026, 3, 9, 18, 30, tzinfo=timezone.utc))
    add_log(db, 8, "WITHDRAWAL", datetime(2026, 3, 10, 18, 29, 59, tzinfo=timezone.utc))
    add_log(db, 7, "DEPOSIT", datetime(2026, 3, 10, 18, 30, tzinfo=timezone.utc))
    act_as("Admin")

    response = client.get(
        "/admin/audit-logs",
        params={"user_id": 7, "action": "DEPOSIT", "from": "2026-03-10", "to": "2026-03-10"},
    )

    assert response.status_code == 200
    assert [row["user_id"] for row in response.json()] == [7]
    assert response.json()[0]["action"] == "DEPOSIT"


@pytest.mark.parametrize("params", [{"from": "2026-03-11", "to": "2026-03-10"}, {"from": "not-a-date"}, {"limit": 501}, {"user_id": 0}])
def test_invalid_audit_log_filters_are_rejected(client, params):
    act_as("Admin")
    assert client.get("/admin/audit-logs", params=params).status_code == 422


def test_empty_results_and_limit_validation(client, db):
    act_as("Admin")
    assert client.get("/admin/audit-logs", params={"action": "MISSING"}).json() == []
    assert client.get("/admin/audit-logs", params={"limit": 500}).status_code == 200


def test_equal_timestamps_are_ordered_by_id_and_get_does_not_mutate_records(client, db):
    timestamp = datetime(2026, 3, 10, 18, 30, tzinfo=timezone.utc)
    older = add_log(db, 7, "OLDER", timestamp)
    newer = add_log(db, 8, "NEWER", timestamp)
    before = [(entry.id, entry.timestamp, entry.action, entry.details) for entry in (older, newer)]
    act_as("Admin")

    response = client.get("/admin/audit-logs")

    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [newer.id, older.id]
    db.expire_all()
    after_entries = [db.get(type(older), entry_id) for entry_id, *_ in before]
    assert [(entry.id, entry.timestamp, entry.action, entry.details) for entry in after_entries] == before
