"""Load sample data for demos and manual testing (US-16). Owner: Member 3 (Ronit).

Run from the repository root:   python -m scripts.seed

Creates 5 customers (2 accounts each = 10 accounts), 3 tellers and 1 admin.
Demo password for EVERY seeded user: Passw0rd!   (demo data only, never use it for anything real)
Customer usernames are the customer IDs (1..5); tellers are teller1..teller3; admin is admin1.
Running it twice does not create duplicates, and running it again after an interrupted run completes the missing data.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import crud
from app.constants import ACCOUNT_CURRENT, ACCOUNT_SAVINGS, ROLE_ADMIN, ROLE_CUSTOMER, ROLE_TELLER
from app.database import Base, SessionLocal, engine
from app.models import Customer
from app.security import hash_password

DEMO_PASSWORD = "Passw0rd!"

CUSTOMERS = [
    ("Asha Rao", date(1990, 3, 14), "12 MG Road, Bengaluru", "9000000001", "asha@example.com"),
    ("Ravi Kumar", date(1985, 7, 2), "5 Anna Salai, Chennai", "9000000002", "ravi@example.com"),
    ("Meera Nair", date(1992, 11, 23), "8 Marine Drive, Kochi", "9000000003", "meera@example.com"),
    ("Karan Shah", date(1988, 1, 9), "21 CG Road, Ahmedabad", "9000000004", "karan@example.com"),
    ("Divya Iyer", date(1995, 5, 30), "3 Park Street, Kolkata", "9000000005", "divya@example.com"),
]


def _ensure_user(db: Session, username: str, role: str, password_hash: str, customer_id: int | None = None) -> None:
    if crud.get_user_by_username(db, username) is None:
        crud.create_user(db, username, password_hash, role, customer_id=customer_id)


def seed(db: Session) -> None:
    """Creates whatever is missing. Safe to run again, also after an earlier run stopped halfway."""
    password_hash = hash_password(DEMO_PASSWORD)
    _ensure_user(db, "admin1", ROLE_ADMIN, password_hash)
    for i in range(1, 4):
        _ensure_user(db, f"teller{i}", ROLE_TELLER, password_hash)

    for index, (name, dob, address, phone, email) in enumerate(CUSTOMERS, start=1):
        id_proof = f"ID-DEMO-{index:04d}"
        customer = db.scalar(select(Customer).where(Customer.id_proof_number == id_proof))
        if customer is None:
            customer = crud.create_customer(
                db,
                name=name,
                date_of_birth=dob,
                address=address,
                phone=phone,
                email=email,
                id_proof_number=id_proof,
            )
        _ensure_user(db, str(customer.id), ROLE_CUSTOMER, password_hash, customer_id=customer.id)

        existing_types = {account.type for account in customer.accounts}
        # known balances: Savings 10,000 x index, Current 20,000 + 5,000 x index
        if ACCOUNT_SAVINGS not in existing_types:
            crud.create_account(db, customer.id, ACCOUNT_SAVINGS, Decimal(10000 * index))
        if ACCOUNT_CURRENT not in existing_types:
            crud.create_account(db, customer.id, ACCOUNT_CURRENT, Decimal(20000 + 5000 * index))


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        seed(session)
    print("Seed data loaded.")
