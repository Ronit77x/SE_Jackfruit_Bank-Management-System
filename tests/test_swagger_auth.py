"""Verify the credential contract used by Swagger UI's Authorize control."""
import pytest

from tests.factories import create_user


PROTECTED = [
    ("/transactions/deposit", "post"),
    ("/transactions/withdraw", "post"),
    ("/transactions/transfer", "post"),
    ("/accounts", "post"),
    ("/accounts", "get"),
    ("/admin/users", "post"),
    ("/auth/unlock", "post"),
    ("/auth/logout", "post"),
]


def test_openapi_declares_http_bearer_for_swagger_authorize(client):
    schema = client.get("/openapi.json").json()
    scheme = schema["components"]["securitySchemes"]["BearerAuth"]
    assert scheme["type"] == "http" and scheme["scheme"] == "bearer"
    assert not schema["paths"]["/auth/login"]["post"].get("security")
    for path, method in PROTECTED:
        operation = schema["paths"][path][method]
        assert {"BearerAuth": []} in operation["security"]
        assert all(p["name"].lower() != "authorization"
                   for p in operation.get("parameters", []) if p["in"] == "header")


@pytest.mark.parametrize("headers", [
    {}, {"Authorization": "Basic invalid"}, {"Authorization": "Bearer"},
    {"Authorization": "Bearer invalid-session"},
])
def test_missing_malformed_and_unknown_credentials_still_return_401(client, headers):
    for method, path, payload in [
        ("get", "/accounts", None),
        ("post", "/auth/logout", None),
        ("post", "/transactions/deposit", {"accountId": "1000000001", "amount": "10"}),
    ]:
        response = client.request(method, path, headers=headers, json=payload)
        assert response.status_code == 401
        assert response.headers.get("www-authenticate") == "Bearer"


def test_swagger_style_bearer_token_supports_protected_request_and_logout(client, db):
    user = create_user(db, role="Teller")
    response = client.post("/auth/login", json={
        "username": user.username, "password": "TestPassword123!",
    })
    assert response.status_code == 200
    headers = {"Authorization": "Bearer " + response.json()["token"]}
    # A Teller is authenticated but not permitted to read Customer accounts.
    assert client.get("/accounts", headers=headers).status_code == 403
    assert client.post("/auth/logout", headers=headers).status_code == 200
    assert client.get("/accounts", headers=headers).status_code == 401
