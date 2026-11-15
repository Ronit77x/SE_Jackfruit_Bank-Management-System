"""Tests for US-05 security helpers."""
import pytest
from cryptography.fernet import Fernet

from app.security import (
    decrypt_value,
    encrypt_value,
    hash_password,
    mask_account_number,
    validate_password_strength,
    verify_password,
)
from app.services.transaction_service import mask_account_number as canonical_mask


@pytest.mark.parametrize(
    "password",
    ["Abcd1234", "StrongPass9", "A1bcdefg"],
)
def test_validate_password_strength_accepts_valid_passwords(password):
    assert validate_password_strength(password) is True


@pytest.mark.parametrize(
    "password",
    ["Abc1234", "abcdefgh1", "ABCDEFGH1", "Abcdefgh", "", None, 12345678],
)
def test_validate_password_strength_rejects_invalid_passwords(password):
    assert validate_password_strength(password) is False


def test_encrypt_and_decrypt_round_trip(monkeypatch):
    monkeypatch.setenv("BMS_DATA_KEY", Fernet.generate_key().decode())

    encrypted = encrypt_value("ID-12345")

    assert encrypted != "ID-12345"
    assert decrypt_value(encrypted) == "ID-12345"


def test_encrypt_supports_empty_string(monkeypatch):
    monkeypatch.setenv("BMS_DATA_KEY", Fernet.generate_key().decode())

    assert decrypt_value(encrypt_value("")) == ""


def test_encryption_requires_key(monkeypatch):
    monkeypatch.delenv("BMS_DATA_KEY", raising=False)

    with pytest.raises(RuntimeError, match="BMS_DATA_KEY is not configured"):
        encrypt_value("secret")


def test_decryption_requires_key(monkeypatch):
    monkeypatch.delenv("BMS_DATA_KEY", raising=False)

    with pytest.raises(RuntimeError, match="BMS_DATA_KEY is not configured"):
        decrypt_value("not-a-token")


@pytest.mark.parametrize("key", ["not-a-fernet-key", "é"])
def test_invalid_key_is_rejected(monkeypatch, key):
    monkeypatch.setenv("BMS_DATA_KEY", key)

    with pytest.raises(RuntimeError, match="BMS_DATA_KEY is invalid"):
        encrypt_value("secret")


def test_invalid_ciphertext_is_rejected_without_exposing_input(monkeypatch):
    monkeypatch.setenv("BMS_DATA_KEY", Fernet.generate_key().decode())
    ciphertext = "not-a-valid-token"

    with pytest.raises(ValueError) as error:
        decrypt_value(ciphertext)

    assert ciphertext not in str(error.value)


def test_wrong_key_is_rejected_without_exposing_plaintext(monkeypatch):
    first_key = Fernet.generate_key().decode()
    monkeypatch.setenv("BMS_DATA_KEY", first_key)
    encrypted = encrypt_value("private-id")
    second_key = Fernet.generate_key().decode()
    monkeypatch.setenv("BMS_DATA_KEY", second_key)

    with pytest.raises(ValueError) as error:
        decrypt_value(encrypted)

    assert "private-id" not in str(error.value)
    assert second_key not in str(error.value)


def test_mask_account_number_reuses_canonical_helper():
    assert mask_account_number("1234567890") == "******7890"
    assert mask_account_number("1234567890") == canonical_mask("1234567890")


def test_existing_bcrypt_helpers_still_work():
    password = "StrongPass9"
    password_hash = hash_password(password)

    assert password_hash != password
    assert verify_password(password, password_hash) is True
    assert verify_password("WrongPass9", password_hash) is False
