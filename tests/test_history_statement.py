"""Transaction history (BMS-F-023) and statement download (BMS-F-024), India Standard Time days."""
import csv
import io
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app import crud
from app.constants import ACCOUNT_SAVINGS
from app.models import Transaction
from app.services import transaction_service as service
from tests.auth_helpers import act_as
from tests.test_crud import _customer


def make_account(db, balance="50000"):
    customer = _customer(db)
    return customer, crud.create_account(db, customer.id, ACCOUNT_SAVINGS, Decimal(balance))


def add_row(db, account, amount, when_utc, txn_type="Deposit", balance_after="50000"):
    db.add(
        Transaction(
            account_id=account.id, type=txn_type, amount=Decimal(amount), balance_after=Decimal(balance_after),
            receipt_no=f"R-{when_utc.timestamp()}", created_at=when_utc,
        )
    )
    db.commit()


def today_ist():
    return datetime.now(service.BANK_TIMEZONE).date()


# ---------- history ----------
def test_without_dates_the_latest_ten_are_returned_newest_first(client, db):
    customer, acct = make_account(db)
    base = datetime.now(timezone.utc) - timedelta(hours=1)
    for i in range(12):
        add_row(db, acct, str(i + 1), base + timedelta(minutes=i))
    act_as("Customer", customer_id=customer.id)
    body = client.get(f"/accounts/{acct.account_number}/transactions").json()
    assert body["miniStatement"] is True and body["count"] == 10
    amounts = [Decimal(t["amount"]) for t in body["transactions"]]
    assert amounts == [Decimal(n) for n in range(12, 2, -1)]  # 12, 11, ... 3
    assert body["account"].endswith(acct.account_number[-4:]) and acct.account_number not in body["account"]


def test_date_range_uses_india_day_boundaries(client, db):
    customer, acct = make_account(db)
    day = today_ist()
    start = service.bank_day_start_utc(day)
    add_row(db, acct, "1", start - timedelta(minutes=1))   # 23:59 the evening before -> outside
    add_row(db, acct, "2", start)                          # exactly 00:00 IST -> inside
    add_row(db, acct, "3", start + timedelta(hours=23, minutes=59))  # 23:59 IST -> inside
    add_row(db, acct, "4", start + timedelta(days=1))      # 00:00 the next day -> outside
    act_as("Customer", customer_id=customer.id)
    body = client.get(f"/accounts/{acct.account_number}/transactions", params={"from": day.isoformat(), "to": day.isoformat()}).json()
    assert body["miniStatement"] is False
    assert sorted(Decimal(t["amount"]) for t in body["transactions"]) == [Decimal("2"), Decimal("3")]
    assert all(t["createdAt"].endswith("+05:30") for t in body["transactions"])


def test_invalid_ranges_are_rejected(client, db):
    customer, acct = make_account(db)
    act_as("Customer", customer_id=customer.id)
    url = f"/accounts/{acct.account_number}/transactions"
    assert client.get(url, params={"from": "2026-10-10", "to": "2026-10-01"}).status_code == 400
    assert client.get(url, params={"from": "2026-10-10"}).status_code == 400
    assert client.get(url, params={"from": "not-a-date", "to": "2026-10-01"}).status_code == 400
    assert client.get("/accounts/123/transactions").status_code == 400  # not a 10-digit account number


def test_history_is_limited_to_the_customers_own_accounts(client, db):
    customer, acct = make_account(db)
    act_as("Customer", customer_id=customer.id + 99)
    assert client.get(f"/accounts/{acct.account_number}/transactions").status_code == 403
    act_as("Customer", customer_id=customer.id)
    assert client.get("/accounts/9999999999/transactions").status_code == 404


def test_other_roles_cannot_read_history(client, db):
    customer, acct = make_account(db)
    act_as("Teller")
    assert client.get(f"/accounts/{acct.account_number}/transactions").status_code == 403


# ---------- statement ----------
def make_activity(db, acct):
    service.deposit(db, acct.account_number, Decimal("500"), 1)
    service.withdraw(db, acct.account_number, Decimal("200"), 1)
    other = crud.create_account(db, acct.customer_id, ACCOUNT_SAVINGS, Decimal("2000"))
    service.transfer(db, acct.account_number, other.account_number, Decimal("100"), 1)


def parse(csv_text):
    return list(csv.reader(io.StringIO(csv_text)))


def test_statement_totals_equal_the_history(client, db):
    customer, acct = make_account(db)
    make_activity(db, acct)
    act_as("Customer", customer_id=customer.id)
    params = {"from": today_ist().isoformat(), "to": today_ist().isoformat()}
    history = client.get(f"/accounts/{acct.account_number}/transactions", params=params).json()["transactions"]
    credits = sum(Decimal(t["amount"]) for t in history if t["type"] in ("Deposit", "OpeningDeposit", "TransferIn"))
    debits = sum(Decimal(t["amount"]) for t in history if t["type"] in ("Withdrawal", "TransferOut"))

    response = client.get(f"/accounts/{acct.account_number}/statement", params={**params, "format": "csv"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"].startswith('attachment; filename="statement-')
    rows = parse(response.text)
    totals = {row[0]: row[1] for row in rows if len(row) == 2}
    assert Decimal(totals["Total credits (Rs)"]) == credits == Decimal("500")
    assert Decimal(totals["Total debits (Rs)"]) == debits == Decimal("300")
    assert int(totals["Number of transactions"]) == len(history) == 3


def test_statement_lists_oldest_first_and_masks_the_account_number(client, db):
    customer, acct = make_account(db)
    make_activity(db, acct)
    act_as("Customer", customer_id=customer.id)
    day = today_ist().isoformat()
    text = client.get(f"/accounts/{acct.account_number}/statement", params={"from": day, "to": day}).text
    assert acct.account_number not in text
    data_rows = [r for r in parse(text) if len(r) == 6 and r[0][:2] == "20"]
    assert [r[1] for r in data_rows] == ["Deposit", "Withdrawal", "TransferOut"]


def test_statement_needs_a_range_and_only_supports_csv(client, db):
    customer, acct = make_account(db)
    act_as("Customer", customer_id=customer.id)
    url = f"/accounts/{acct.account_number}/statement"
    assert client.get(url).status_code == 400
    day = today_ist().isoformat()
    response = client.get(url, params={"from": day, "to": day, "format": "pdf"})
    assert response.status_code == 400 and response.json()["code"] == "UNSUPPORTED_FORMAT"


def test_statement_is_limited_to_the_customers_own_accounts(client, db):
    customer, acct = make_account(db)
    act_as("Customer", customer_id=customer.id + 99)
    day = today_ist().isoformat()
    assert client.get(f"/accounts/{acct.account_number}/statement", params={"from": day, "to": day}).status_code == 403


def test_spreadsheet_formulas_are_neutralised():
    assert service._csv_safe("=1+1") == "'=1+1"
    assert service._csv_safe("@cmd") == "'@cmd"
    assert service._csv_safe("Deposit") == "Deposit"
