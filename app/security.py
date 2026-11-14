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


def validate_password_complexity(password: str) -> tuple[bool, str]:
    """Validate password complexity (BMS-F-004, US-04).

    Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    return True, ""
