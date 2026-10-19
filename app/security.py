"""Password hashing helpers. Owner: Member 1 (Tarini), story US-05 (BMS-SR-002).

The two functions below are a working starting point so that other members (for example the
seed script and account opening) can already create users. Tarini extends this file
(password policy, session timeout, masking) but keeps these function names.
"""
import bcrypt


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, password_hash: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), password_hash.encode("utf-8"))
