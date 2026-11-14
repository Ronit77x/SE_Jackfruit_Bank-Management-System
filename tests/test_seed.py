import pytest
from cryptography.fernet import Fernet
from app.security import decrypt_value
from tests.factories import create_account, create_customer
from sqlalchemy import func, select

from app.models import Account, Customer, User
from scripts.seed import seed


@pytest.fixture(autouse=True)
def seed_key(monkeypatch):
    monkeypatch.setenv("BMS_DATA_KEY", Fernet.generate_key().decode())


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


def test_seed_encrypts_ids_and_preserves_ciphertext_on_repeat(db):
    seed(db)
    first = {row.id: row.id_proof_number for row in db.scalars(select(Customer))}
    assert {decrypt_value(value) for value in first.values()} == {
        f"ID-DEMO-{i:04d}" for i in range(1, 6)
    }
    assert all(not value.startswith("ID-DEMO-") for value in first.values())
    seed(db)
    assert {row.id: row.id_proof_number for row in db.scalars(select(Customer))} == first


def test_seed_upgrades_legacy_demo_id_without_changing_accounts_or_balance(db):
    legacy = create_customer(db, id_proof_number="ID-DEMO-0001")
    account = create_account(db, customer=legacy, account_number="1000000001", balance=12345)
    original_id = legacy.id
    seed(db)
    db.refresh(account)
    db.refresh(legacy)
    assert legacy.id == original_id
    assert decrypt_value(legacy.id_proof_number) == "ID-DEMO-0001"
    assert legacy.id_proof_number != "ID-DEMO-0001"
    assert account.balance == 12345
    assert db.query(Account).filter_by(account_number="1000000001").count() == 1
    assert db.query(Customer).count() == 5
    assert db.query(Account).count() == 10
    seed(db)
    assert db.query(Customer).count() == 5
    assert db.query(Account).count() == 10


@pytest.mark.parametrize("key", [None, "invalid-key"])
def test_missing_or_invalid_key_fails_before_creating_any_records(db, monkeypatch, key):
    if key is None:
        monkeypatch.delenv("BMS_DATA_KEY")
    else:
        monkeypatch.setenv("BMS_DATA_KEY", key)
    with pytest.raises(RuntimeError):
        seed(db)
    assert db.query(Customer).count() == db.query(User).count() == db.query(Account).count() == 0


def test_wrong_key_does_not_overwrite_or_duplicate_existing_seed_data(db, monkeypatch):
    seed(db)
    before = {row.id: row.id_proof_number for row in db.scalars(select(Customer))}
    monkeypatch.setenv("BMS_DATA_KEY", Fernet.generate_key().decode())
    with pytest.raises(RuntimeError, match="cannot be read"):
        seed(db)
    assert {row.id: row.id_proof_number for row in db.scalars(select(Customer))} == before
    assert db.query(Customer).count() == 5
    assert db.query(Account).count() == 10


def test_seed_leaves_unrelated_plaintext_records_unchanged(db):
    unrelated = create_customer(db, id_proof_number="UNRELATED-LEGACY-ID")
    seed(db)
    db.refresh(unrelated)
    assert unrelated.id_proof_number == "UNRELATED-LEGACY-ID"
    assert db.query(Customer).count() == 6
