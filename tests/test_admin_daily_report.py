from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app import crud
from app.constants import ACCOUNT_SAVINGS, TXN_DEPOSIT, TXN_OPENING_DEPOSIT, TXN_TRANSFER_IN, TXN_TRANSFER_OUT, TXN_WITHDRAWAL
from app.models import Transaction
from tests.auth_helpers import act_as


def add_account(db, number):
    customer = crud.create_customer(
        db,
        name=f"Customer {number}",
        date_of_birth=datetime(1990, 1, 1).date(),
        address="Address",
        phone="9999999999",
        email=f"{number}@example.com",
        id_proof_number="encrypted",
    )
    return crud.create_account(db, customer.id, ACCOUNT_SAVINGS, Decimal("10000"), account_number=number)


def add_txn(db, account_id, txn_type, amount, created_at, reference=None):
    txn = Transaction(
        account_id=account_id,
        type=txn_type,
        amount=Decimal(amount),
        balance_after=Decimal("10000"),
        reference=reference,
        created_at=created_at,
    )
    db.add(txn)
    db.commit()
    return txn


def report(client, report_date="2026-03-10"):
    return client.get("/admin/reports/daily", params={"date": report_date})


def test_admin_report_aggregates_bank_wide_activity_and_transfer_once(client, db):
    first = add_account(db, "1000000001")
    second = add_account(db, "1000000002")
    day = datetime(2026, 3, 9, 18, 30, tzinfo=timezone.utc)
    add_txn(db, first.id, TXN_DEPOSIT, "125.10", day)
    add_txn(db, second.id, TXN_WITHDRAWAL, "20.25", day)
    add_txn(db, first.id, TXN_TRANSFER_OUT, "50.00", day, "TRF-1")
    add_txn(db, second.id, TXN_TRANSFER_IN, "50.00", day, "TRF-1")
    act_as("Admin")

    response = report(client)

    assert response.status_code == 200
    body = response.json()
    assert body["report_date"] == "2026-03-10"
    assert body["timezone"] == "Asia/Kolkata"
    assert body["deposits"]["count"] == 1
    assert Decimal(str(body["deposits"]["total_amount"])) == Decimal("125.10")
    assert body["withdrawals"]["count"] == 1
    assert Decimal(str(body["withdrawals"]["total_amount"])) == Decimal("20.25")
    assert body["transfers"] == {"count": 1, "total_amount": "50.00"}


def test_opening_deposits_are_transparent_deposit_subcategory(client, db):
    account = add_account(db, "1000000003")
    add_txn(db, account.id, TXN_OPENING_DEPOSIT, "1000.00", datetime(2026, 3, 9, 18, 30))
    act_as("Admin")

    body = report(client).json()

    assert body["deposits"]["count"] == 1
    assert body["deposits"]["opening_deposits"] == {"count": 1, "total_amount": "1000.00"}


def test_report_uses_half_open_ist_day_boundaries(client, db):
    account = add_account(db, "1000000004")
    add_txn(db, account.id, TXN_DEPOSIT, "1", datetime(2026, 3, 9, 18, 29, 59))
    add_txn(db, account.id, TXN_DEPOSIT, "2", datetime(2026, 3, 9, 18, 30))
    add_txn(db, account.id, TXN_DEPOSIT, "3", datetime(2026, 3, 10, 18, 29, 59))
    add_txn(db, account.id, TXN_DEPOSIT, "4", datetime(2026, 3, 10, 18, 30))
    act_as("Admin")

    body = report(client).json()

    assert body["deposits"]["count"] == 2
    assert Decimal(str(body["deposits"]["total_amount"])) == Decimal("5.00")


@pytest.mark.parametrize("role", ["Customer", "Teller"])
def test_only_admin_can_generate_report(client, role):
    act_as(role)
    assert report(client).status_code == 403


def test_unauthenticated_report_is_rejected(client):
    assert report(client).status_code == 401


@pytest.mark.parametrize("params", [{}, {"date": "not-a-date"}, {"date": "2026-02-30"}])
def test_report_date_is_required_and_valid(client, params):
    act_as("Admin")
    assert client.get("/admin/reports/daily", params=params).status_code in (400, 422)


def test_empty_day_returns_zero_values_and_records_safe_audit_event(client, db):
    act_as("Admin", user_id=42)

    response = report(client)

    assert response.status_code == 200
    body = response.json()
    assert body["deposits"] == {"count": 0, "total_amount": "0.00", "opening_deposits": {"count": 0, "total_amount": "0.00"}}
    assert body["withdrawals"] == {"count": 0, "total_amount": "0.00"}
    assert body["transfers"] == {"count": 0, "total_amount": "0.00"}
    audit = db.query(__import__("app.models", fromlist=["AuditLog"]).AuditLog).one()
    assert (audit.user_id, audit.action, audit.details) == (42, "DAILY_REPORT_GENERATED", "report_date=2026-03-10")
    assert set(body) == {"report_date", "timezone", "generated_at", "deposits", "withdrawals", "transfers"}
