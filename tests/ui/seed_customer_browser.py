"""Create disposable data for customer_browser_check.js; refuses an existing DB.

Run from the repository root with: python -m tests.ui.seed_customer_browser
Set BMS_DATABASE_URL to a NEW absolute SQLite file under a temporary directory.
Never use a real project database. These are synthetic display fixtures, not
performance or financial-reconciliation evidence.
"""
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy.engine import make_url


def main():
    url = make_url(os.environ["BMS_DATABASE_URL"])
    if url.get_backend_name() != "sqlite" or not url.database:
        raise SystemExit("A new absolute SQLite file is required.")
    target = Path(url.database)
    if not target.is_absolute() or target.exists() or not target.parent.is_dir():
        raise SystemExit("Refusing an existing or non-absolute database, or a missing parent directory.")
    from app.database import Base, engine, SessionLocal
    from app.models import Transaction
    from tests.factories import create_account, create_user
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        user = create_user(db, username="ui_customer")
        account = create_account(db, customer_id=user.customer_id, account_number="1234567890",
                                 balance=Decimal("123456789012.99"))
        create_account(db, customer_id=user.customer_id, account_number="9876547890", status="Frozen")
        for index in range(61):
            db.add(Transaction(account_id=account.id, type="Deposit", amount=Decimal("1.01"),
                               balance_after=Decimal("1500.00"), receipt_no=f"DEMO-{index}",
                               created_at=datetime.now(timezone.utc)))
        create_user(db, username="ui_empty")
        db.commit()
    print("Disposable customer UI fixtures created.")


if __name__ == "__main__":
    main()
