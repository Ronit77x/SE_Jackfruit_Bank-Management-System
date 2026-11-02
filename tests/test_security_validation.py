from decimal import Decimal

from app import crud
from app.constants import ACCOUNT_SAVINGS, ROLE_CUSTOMER
from tests.test_crud import _customer
from tests.auth_helpers import act_as


def make_account(db):
    return crud.create_account(db, _customer(db).id, ACCOUNT_SAVINGS, Decimal("10000"))


def test_account_identifier_rejects_injection_and_unicode_digits_without_changes(client, db):
    act_as("Teller")
    account = make_account(db)
    for value in ("9999999999' OR '1'='1", "１２３４５６７８９０", "<script>alert(1)</script>"):
        response = client.post("/transactions/deposit", json={"accountId": value, "amount": "100"})
        assert response.status_code == 400
    db.refresh(account)
    assert account.balance == Decimal("10000.00")


def test_amount_validation_rejects_non_positive_and_unsupported_precision(client, db):
    act_as("Teller")
    account = make_account(db)
    for value in ("0", "-1", "1.001"):
        response = client.post("/transactions/deposit", json={"accountId": account.account_number, "amount": value})
        assert response.status_code == 400
    db.refresh(account)
    assert account.balance == Decimal("10000.00")


def test_unexpected_request_fields_are_rejected(client, db):
    act_as("Teller")
    account = make_account(db)
    response = client.post(
        "/transactions/deposit",
        json={"accountId": account.account_number, "amount": "100", "admin": "<script>"},
    )
    assert response.status_code == 400


def test_https_config_allows_only_tls_12_and_newer():
    config = open("deploy/nginx-https.conf", encoding="utf-8").read()
    assert "ssl_protocols       TLSv1.2 TLSv1.3;" in config
    assert "ssl_certificate_key" in config
    assert "BEGIN PRIVATE KEY" not in config


def test_transaction_validation_requires_login(client, db):
    account = make_account(db)

    response = client.post(
        "/transactions/deposit",
        json={"accountId": account.account_number, "amount": "100"},
    )

    assert response.status_code == 401


def test_wrong_role_is_rejected_and_audited(client, db):
    account = make_account(db)
    act_as(ROLE_CUSTOMER, customer_id=account.customer_id)

    response = client.post(
        "/transactions/deposit",
        json={"accountId": account.account_number, "amount": "100"},
    )

    assert response.status_code == 403
