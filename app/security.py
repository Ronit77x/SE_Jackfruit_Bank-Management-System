"""Password and sensitive-data security helpers for US-05.

The two functions below are a working starting point so that other members (for example the
The hashing functions remain compatible with the authentication and seed code.
"""
import os

import bcrypt
from cryptography.fernet import Fernet, InvalidToken

from app.services.transaction_service import mask_account_number


_DATA_KEY_ENV = "BMS_DATA_KEY"


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, password_hash: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), password_hash.encode("utf-8"))


def validate_password_strength(password) -> bool:
    """Return whether *password* meets the agreed minimum password policy."""
    if not isinstance(password, str) or len(password) < 8:
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
