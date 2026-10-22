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
