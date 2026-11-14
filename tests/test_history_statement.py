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


# ---------- large accounts: nothing may be cut off silently ----------
def make_many(db, acct, credits=1000, debits=500):
    """1,500 transactions today (India time): `credits` deposits of Rs 2 and `debits` withdrawals of Rs 3."""
    start = service.bank_day_start_utc(today_ist())
    rows = []
    for i in range(credits + debits):
        is_credit = i < credits
        rows.append(
            Transaction(
                account_id=acct.id,
                type="Deposit" if is_credit else "Withdrawal",
                amount=Decimal("2") if is_credit else Decimal("3"),
                balance_after=Decimal("50000"),
                receipt_no=f"BULK-{i}",
                created_at=start + timedelta(seconds=i),
            )
        )
    db.add_all(rows)
    db.commit()
    return credits, debits


def test_statement_of_more_than_1000_transactions_is_complete_and_accurate(client, db):
    customer, acct = make_account(db)
    make_many(db, acct)
    act_as("Customer", customer_id=customer.id)
    day = today_ist().isoformat()
    response = client.get(f"/accounts/{acct.account_number}/statement", params={"from": day, "to": day})
    assert response.status_code == 200
    rows = parse(response.text)
    totals = {row[0]: row[1] for row in rows if len(row) == 2}
    assert int(totals["Number of transactions"]) == 1500
    assert Decimal(totals["Total credits (Rs)"]) == Decimal("2000.00")  # 1,000 x Rs 2
    assert Decimal(totals["Total debits (Rs)"]) == Decimal("1500.00")   # 500 x Rs 3
    data_rows = [r for r in rows if len(r) == 6 and r[0][:2] == "20"]
    assert len(data_rows) == 1500  # every transaction is listed, none dropped


def test_history_is_paged_and_says_how_many_there_are(client, db):
    customer, acct = make_account(db)
    make_many(db, acct)
    act_as("Customer", customer_id=customer.id)
    day = today_ist().isoformat()
    url = f"/accounts/{acct.account_number}/transactions"

    first = client.get(url, params={"from": day, "to": day, "limit": 100}).json()
    assert (first["total"], first["count"], first["hasMore"]) == (1500, 100, True)

    last = client.get(url, params={"from": day, "to": day, "limit": 100, "offset": 1400}).json()
    assert (last["count"], last["hasMore"]) == (100, False)

    ids = []
    offset = 0
    while True:
        page = client.get(url, params={"from": day, "to": day, "limit": 1000, "offset": offset}).json()
        ids += [t["transactionId"] for t in page["transactions"]]
        if not page["hasMore"]:
            break
        offset += 1000
    assert len(ids) == len(set(ids)) == 1500  # the pages together cover everything exactly once


def test_page_parameters_are_validated(client, db):
    customer, acct = make_account(db)
    act_as("Customer", customer_id=customer.id)
    day = today_ist().isoformat()
    url = f"/accounts/{acct.account_number}/transactions"
    for params in ({"limit": 0}, {"limit": 1001}, {"offset": -1}):
        assert client.get(url, params={"from": day, "to": day, **params}).status_code == 400


def test_mini_statement_reports_that_more_transactions_exist(client, db):
    customer, acct = make_account(db)
    make_many(db, acct, credits=15, debits=0)
    act_as("Customer", customer_id=customer.id)
    body = client.get(f"/accounts/{acct.account_number}/transactions").json()
    assert (body["miniStatement"], body["count"], body["total"], body["hasMore"]) == (True, 10, 15, True)


# ---------- audit of statement downloads ----------
def test_statement_download_is_audited_with_the_masked_account_only(client, db):
    from app.models import AuditLog

    customer, acct = make_account(db)
    make_activity(db, acct)
    act_as("Customer", customer_id=customer.id, user_id=42)
    day = today_ist().isoformat()
    assert client.get(f"/accounts/{acct.account_number}/statement", params={"from": day, "to": day}).status_code == 200
    (entry,) = db.query(AuditLog).filter_by(action="STATEMENT_DOWNLOAD").all()
    assert entry.user_id == 42 and entry.outcome == "SUCCESS"
    assert acct.account_number not in entry.details and acct.account_number[-4:] in entry.details
    assert "rows 3" in entry.details


def test_a_denied_download_is_not_recorded_as_a_download(client, db):
    from app.models import AuditLog

    customer, acct = make_account(db)
    act_as("Customer", customer_id=customer.id + 99)
    day = today_ist().isoformat()
    assert client.get(f"/accounts/{acct.account_number}/statement", params={"from": day, "to": day}).status_code == 403
    assert db.query(AuditLog).filter_by(action="STATEMENT_DOWNLOAD").count() == 0


def test_statement_audit_storage_failure_returns_no_csv_and_rolls_back(client, db):
    from sqlalchemy import event
    from app.models import AuditLog

    customer, acct = make_account(db)
    make_activity(db, acct)
    act_as("Customer", customer_id=customer.id)
    before = db.query(AuditLog).count()

    def reject_statement_audit(session, flush_context, instances):
        if any(isinstance(row, AuditLog) and row.action == "STATEMENT_DOWNLOAD" for row in session.new):
            raise RuntimeError("private audit database error")

    event.listen(db, "before_flush", reject_statement_audit)
    day = today_ist().isoformat()
    try:
        response = client.get(f"/accounts/{acct.account_number}/statement", params={"from": day, "to": day})
    finally:
        event.remove(db, "before_flush", reject_statement_audit)
    assert response.status_code == 503
    assert response.json()["code"] == "STATEMENT_AUDIT_UNAVAILABLE"
    assert response.headers["content-type"].startswith("application/json")
    assert "content-disposition" not in response.headers
    assert "private audit" not in response.text and acct.account_number not in response.text
    assert db.query(AuditLog).count() == before
    # The failed session is usable again; a retry succeeds and is audited once.
    retry = client.get(f"/accounts/{acct.account_number}/statement", params={"from": day, "to": day})
    assert retry.status_code == 200
    assert db.query(AuditLog).filter_by(action="STATEMENT_DOWNLOAD").count() == 1
