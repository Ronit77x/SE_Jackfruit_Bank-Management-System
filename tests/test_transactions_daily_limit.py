"""The daily withdrawal limit (BR-02) uses the India Standard Time day, not the UTC day."""
from datetime import timedelta
from decimal import Decimal

import pytest

from app import crud
from app.errors import AppError
from app.models import Transaction
from app.services import transaction_service as service
from tests.test_crud import _customer


def _account_with_earlier_withdrawal(db, withdrawn_at):
    account = crud.create_account(db, _customer(db).id, "Savings", Decimal("200000"))
    db.add(
        Transaction(
            account_id=account.id,
            type="Withdrawal",
            amount=Decimal("45000"),
            balance_after=Decimal("155000"),
            created_at=withdrawn_at,
        )
    )
    db.commit()
    return account


def test_withdrawal_just_before_ist_midnight_does_not_count_today(db):
    start = service._start_of_bank_day_utc()
    account = _account_with_earlier_withdrawal(db, start - timedelta(minutes=1))
    txn = service.withdraw(db, account.account_number, Decimal("10000"), 1)  # 45,000 + 10,000 would exceed only if it counted
    assert txn.amount == Decimal("10000.00")


def test_withdrawal_since_ist_midnight_counts_today(db):
    start = service._start_of_bank_day_utc()
    account = _account_with_earlier_withdrawal(db, start)
    with pytest.raises(AppError) as error:
        service.withdraw(db, account.account_number, Decimal("10000"), 1)
    assert error.value.code == "DAILY_LIMIT_EXCEEDED"


def test_start_of_bank_day_is_midnight_ist():
    start = service._start_of_bank_day_utc()
    local = start.astimezone(service.BANK_TIMEZONE)
    assert (local.hour, local.minute, local.second) == (0, 0, 0)
