"""Password and sensitive-data security helpers for US-04 and US-05.

The hashing functions remain compatible with the authentication and seed code.
Bcrypt has an architectural input limit of 72 bytes. Passwords are validated
against this limit in UTF-8 byte length (not character count) to avoid unhandled
500 errors or silent truncation.
"""
import os

import bcrypt
from cryptography.fernet import Fernet, InvalidToken

from app.services.transaction_service import mask_account_number

_DATA_KEY_ENV = "BMS_DATA_KEY"
MAX_PASSWORD_BYTES = 72


def hash_password(plain: str) -> str:
    encoded = plain.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password cannot exceed {MAX_PASSWORD_BYTES} bytes")
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, password_hash: str) -> bool:
    try:
        encoded = plain.encode("utf-8")
        if len(encoded) > MAX_PASSWORD_BYTES:
            return False
        return bcrypt.checkpw(encoded, password_hash.encode("utf-8"))
    except Exception:
        return False


def validate_password_complexity(password: str) -> tuple[bool, str]:
    """Validate password complexity and length (BMS-F-004, US-04).

    Requirements:
    - Minimum 8 characters
    - Maximum 72 UTF-8 bytes (bcrypt limit)
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    """
    if not isinstance(password, str):
        return False, "Password must be a string"
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        return False, f"Password cannot exceed {MAX_PASSWORD_BYTES} bytes"
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    return True, ""


def validate_password_strength(password) -> bool:
    """Return whether *password* meets the agreed minimum password policy."""
    if not isinstance(password, str) or len(password) < 8:
        return False
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        return False
    return (
        any(character.isupper() for character in password)
        and any(character.islower() for character in password)
        and any(character.isdigit() for character in password)
    )


def _fernet() -> Fernet:
    key = os.environ.get(_DATA_KEY_ENV)
    if not key:
        raise RuntimeError(f"{_DATA_KEY_ENV} is not configured")
    try:
        return Fernet(key.encode("ascii"))
    except (UnicodeEncodeError, ValueError) as exc:
        raise RuntimeError(f"{_DATA_KEY_ENV} is invalid") from exc


def encrypt_value(value: str) -> str:
    """Encrypt a string value using the configured Fernet key."""
    if not isinstance(value, str):
        raise TypeError("value must be a string")
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_value(encrypted_value: str) -> str:
    """Decrypt a Fernet token using the configured key."""
    if not isinstance(encrypted_value, str):
        raise TypeError("encrypted_value must be a string")
    try:
        return _fernet().decrypt(encrypted_value.encode("ascii")).decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError, InvalidToken) as exc:
        raise ValueError("Invalid encrypted value") from exc
