"""Read-only reconciliation of a fresh seeded R3 benchmark against Locust counts.

Usage: python tests/load/check_load_ledger.py --run <external-output>/R3-1
The run folder must contain benchmark.db and load_stats.csv from the runner.
"""
import argparse
from collections import Counter, defaultdict
import csv
from decimal import Decimal
import json
from pathlib import Path
import sqlite3


def reconcile(folder):
    with (folder / "load_stats.csv").open(newline="", encoding="utf-8") as stream:
        stats = {row["Name"]: row for row in csv.DictReader(stream)}
    counts = {}
    for endpoint, action in (("deposit", "DEPOSIT"), ("withdraw", "WITHDRAWAL"), ("transfer", "TRANSFER")):
        row = stats["/transactions/" + endpoint]
        assert int(row["Failure Count"]) == 0, row
        counts[action] = int(row["Request Count"])
    database = folder / "benchmark.db"
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        accounts = list(db.execute("SELECT * FROM accounts ORDER BY id"))
        transactions = list(db.execute("SELECT * FROM transactions ORDER BY id"))
        notifications = list(db.execute("SELECT customer_id, message FROM notifications"))
        audits = Counter({row["action"]: row["n"] for row in db.execute(
            "SELECT action, count(*) AS n FROM audit_logs WHERE outcome='SUCCESS' GROUP BY action")})
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert list(db.execute("PRAGMA foreign_key_check")) == []
        triggers = {row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='audit_logs'")}
    assert triggers == {"audit_logs_append_only_update", "audit_logs_append_only_delete"}
    assert len(accounts) == 10
    by_id = {account["id"]: account for account in accounts}
    initial = {account["id"]: Decimal(10000 * account["customer_id"] if account["type"] == "Savings"
                                    else 20000 + 5000 * account["customer_id"]) for account in accounts}
    balances = initial.copy()
    transaction_counts = Counter()
    references = defaultdict(list)
    expected_notifications = Counter()
    labels = {"Deposit": "Deposit", "Withdrawal": "Withdrawal",
              "TransferOut": "Transfer sent", "TransferIn": "Transfer received"}
    for row in transactions:
        kind = row["type"]
        assert kind in labels, kind
        amount = Decimal(str(row["amount"]))
        assert amount == Decimal("1"), row["id"]
        account = by_id[row["account_id"]]
        balance = balances[account["id"]] + (amount if kind in ("Deposit", "TransferIn") else -amount)
        assert balance == Decimal(str(row["balance_after"])), row["id"]
        balances[account["id"]] = balance
        transaction_counts[kind] += 1
        if kind.startswith("Transfer"):
            assert row["reference"]
            references[row["reference"]].append(row)
        masked = "******" + account["account_number"][-4:]
        direction = "to" if kind in ("Deposit", "TransferIn") else "from"
        message = f"{labels[kind]} of Rs {amount:,.2f} {direction} account {masked}. New balance: Rs {balance:,.2f}."
        expected_notifications[(account["customer_id"], message)] += 1
    expected_counts = {"Deposit": counts["DEPOSIT"], "Withdrawal": counts["WITHDRAWAL"],
                       "TransferOut": counts["TRANSFER"], "TransferIn": counts["TRANSFER"]}
    assert dict(transaction_counts) == expected_counts, (transaction_counts, expected_counts)
    assert len(references) == counts["TRANSFER"]
    for reference, pair in references.items():
        assert len(pair) == 2 and {row["type"] for row in pair} == {"TransferOut", "TransferIn"}, reference
        assert pair[0]["amount"] == pair[1]["amount"] and pair[0]["account_id"] != pair[1]["account_id"], reference
    assert Counter((row["customer_id"], row["message"]) for row in notifications) == expected_notifications
    assert audits == Counter({**counts, "LOGIN": 50}), audits
    for account in accounts:
        assert balances[account["id"]] == Decimal(str(account["balance"])), account["id"]
    initial_total = sum(initial.values())
    final_total = sum(balances.values())
    assert final_total == initial_total + counts["DEPOSIT"] - counts["WITHDRAWAL"]
    manifest = json.loads((folder.parent / "results.json").read_text(encoding="utf-8"))
    return {
        "source_commit": manifest["source_commit"], "accounts_reconciled": len(accounts),
        "transaction_counts": dict(transaction_counts), "transaction_rows": len(transactions),
        "notification_rows": len(notifications), "successful_audit_counts": dict(audits),
        "initial_total_balance": str(initial_total), "final_total_balance": str(final_total),
        "all_account_balances_match_seed_plus_ledger": True,
        "every_intermediate_balance_matches_ledger": True,
        "transfer_pairs_reconciled": len(references),
        "notification_contents_and_customers_match_transactions": True,
        "notification_count_matches_transaction_rows": True,
        "sqlite_integrity_check": "ok", "foreign_key_violations": 0,
        "append_only_triggers_installed": sorted(triggers),
        "note": "Read-only inspection of disposable benchmark data; transfers have two ledger rows per request."
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(reconcile(args.run.resolve()), indent=2, sort_keys=True))
