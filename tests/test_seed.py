import pytest
from sqlalchemy import func, select

from app.models import Account, Customer, User
from scripts.seed import seed


def test_seed_creates_expected_data_once(db):
    seed(db)
    seed(db)  # second run must not duplicate anything
    assert db.scalar(select(func.count()).select_from(Customer)) == 5
    assert db.scalar(select(func.count()).select_from(Account)) == 10
    assert db.scalar(select(func.count()).select_from(User).where(User.role == "Teller")) == 3
    assert db.scalar(select(func.count()).select_from(User).where(User.role == "Admin")) == 1


def test_seed_completes_missing_data_after_an_interrupted_run(db, monkeypatch):
    from app import crud

    real_create_account = crud.create_account
    calls = {"count": 0}

    def crash_on_fourth_account(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 4:
            raise RuntimeError("simulated crash in the middle of seeding")
        return real_create_account(*args, **kwargs)

    monkeypatch.setattr(crud, "create_account", crash_on_fourth_account)
    with pytest.raises(RuntimeError):
        seed(db)  # the simulated crash must really happen, otherwise this test proves nothing
    monkeypatch.setattr(crud, "create_account", real_create_account)

    seed(db)  # second run must finish the job without duplicates
    assert db.scalar(select(func.count()).select_from(Customer)) == 5
    assert db.scalar(select(func.count()).select_from(Account)) == 10
    assert db.scalar(select(func.count()).select_from(User).where(User.role == "Customer")) == 5
    assert db.scalar(select(func.count()).select_from(User).where(User.role == "Teller")) == 3
