"""Real-login contract checks for the customer page's owned-ID API."""
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.models import AuditLog, Transaction
from app.routers import transactions
from tests.factories import create_account, create_user
from tests.test_account_integration import login


def fixture_activity(client, db, count=31):
    user = create_user(db)
    own = create_account(db, customer_id=user.customer_id)
    other = create_account(db)
    for i in range(count):
        db.add(Transaction(account_id=own.id, type="Deposit", amount=Decimal("0.01"),
                           balance_after=Decimal("1500.00"), created_at=datetime.now(timezone.utc)))
    db.commit()
    return own, other, login(client, user)


def period():
    return {"from": "2020-01-01", "to": "2099-12-31"}


def test_login_list_to_masked_history_pagination_and_complete_csv(client, db):
    own, other, headers = fixture_activity(client, db)
    listed = client.get("/accounts", headers=headers)
    assert listed.status_code == 200
    assert own.account_number not in listed.text
    assert listed.json()["accounts"][0]["account_id"] == own.id
    path = f"/accounts/by-id/{own.id}"
    mini = client.get(path + "/transactions", headers=headers).json()
    assert mini["count"] == 10 and mini["total"] == 31 and mini["miniStatement"]
    first = client.get(path + "/transactions", headers=headers, params={**period(), "limit": 25}).json()
    second = client.get(path + "/transactions", headers=headers, params={**period(), "limit": 25, "offset": 25}).json()
    assert first["count"] == 25 and first["hasMore"]
    assert second["count"] == 6 and not second["hasMore"]
    assert len({x["transactionId"] for x in first["transactions"] + second["transactions"]}) == 31
    csv = client.get(path + "/statement", headers=headers, params=period())
    assert csv.status_code == 200 and "text/csv" in csv.headers["content-type"]
    assert 'Number of transactions,31' in csv.text
    assert own.account_number not in csv.text
    assert db.query(AuditLog).filter_by(action="STATEMENT_DOWNLOAD").count() == 1


@pytest.mark.parametrize("suffix", ["transactions", "statement"])
def test_id_is_not_authority_and_unauthorized_accounts_look_absent(client, db, suffix):
    own, other, headers = fixture_activity(client, db, 0)
    for account_id in (other.id, 999999):
        response = client.get(f"/accounts/by-id/{account_id}/{suffix}", headers=headers, params=period())
        assert response.status_code == 404
        assert response.json()["code"] == "ACCOUNT_NOT_FOUND"
    path = f"/accounts/by-id/{own.id}/{suffix}"
    assert client.get(path, params=period()).status_code == 401
    for role in ("Teller", "Admin"):
        assert client.get(path, headers=login(client, create_user(db, role=role)), params=period()).status_code == 403
    temporary = create_user(db, customer_id=own.customer_id, must_change_password=True)
    assert client.get(path, headers=login(client, temporary), params=period()).status_code == 403


def test_id_export_still_fails_closed_when_audit_fails(client, db, monkeypatch):
    own, _, headers = fixture_activity(client, db, 1)
    def fail(*args, **kwargs):
        raise RuntimeError("simulated audit failure")
    monkeypatch.setattr(transactions, "log_event", fail)
    response = client.get(f"/accounts/by-id/{own.id}/statement", headers=headers, params=period())
    assert response.status_code == 503
    assert response.json()["code"] == "STATEMENT_AUDIT_UNAVAILABLE"
    assert "content-disposition" not in response.headers
    assert "text/csv" not in response.headers["content-type"]


def test_id_history_empty_and_invalid_range_and_static_entry(client, db):
    own, _, headers = fixture_activity(client, db, 0)
    path = f"/accounts/by-id/{own.id}"
    assert client.get(path + "/transactions", headers=headers).json()["transactions"] == []
    assert client.get(path + "/transactions", headers=headers, params={"from": "2026-02-02", "to": "2026-01-01"}).status_code == 400
    assert client.get(path + "/statement", headers=headers, params={**period(), "format": "pdf"}).status_code == 400
    assert client.get("/ui/customer.html").status_code == 200
    assert client.get("/ui/js/customer.js").status_code == 200
