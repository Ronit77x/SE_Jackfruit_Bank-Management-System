"""Tests for the browser-based change password page (/ui/change-password.html) and UI flow."""
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi import status

from app.security import hash_password
from tests.factories import create_user

ROOT = Path(__file__).resolve().parent.parent


def test_change_password_page_is_served(client):
    """Verify that /ui/change-password.html is served with required responsive layout and controls."""
    resp = client.get("/ui/change-password.html")
    assert resp.status_code == status.HTTP_200_OK
    assert 'name="viewport"' in resp.text
    assert "/ui/css/style.css" in resp.text
    assert "/ui/js/api.js" in resp.text
    assert 'id="change-password-form"' in resp.text
    assert 'id="current-password"' in resp.text
    assert 'id="new-password"' in resp.text
    assert 'id="confirm-password"' in resp.text
    assert 'toggle-password' in resp.text
    assert 'id="mandatory-notice"' in resp.text
    assert 'id="change-message"' in resp.text
    assert 'id="submit-btn"' in resp.text
    assert 'id="continue-btn"' in resp.text


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")
def test_change_password_ui_node_checks():
    """Run Node.js behavioral tests for change-password.html covering DOM, validation, toggles and reset."""
    result = subprocess.run(
        ["node", str(ROOT / "tests" / "ui" / "change_password_check.js")],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_first_login_mandatory_reset_flow(client, db):
    """Verify end-to-end mandatory password change: login with temp password, block role access,

    change password, verify access unblocked and mustChangePassword cleared.
    """
    user = create_user(
        db,
        username="temp-cust-33",
        password_hash=hash_password("TempPass123!"),
        must_change_password=True,
    )

    # 1. Login returns mustChangePassword=True
    login_resp = client.post(
        "/auth/login",
        json={"username": "temp-cust-33", "password": "TempPass123!"},
    )
    assert login_resp.status_code == status.HTTP_200_OK
    data = login_resp.json()
    assert data["mustChangePassword"] is True
    token = data["token"]

    # 2. Access to customer accounts is blocked by temporary password requirement
    accounts_resp = client.get(
        "/accounts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert accounts_resp.status_code == status.HTTP_403_FORBIDDEN
    assert "temporary password" in accounts_resp.json()["detail"].lower()

    # 3. Change password with incorrect current password is rejected
    wrong_curr = client.post(
        "/auth/change-password",
        json={"currentPassword": "WrongPass123!", "newPassword": "NewStrongPass1!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert wrong_curr.status_code == status.HTTP_400_BAD_REQUEST
    assert "Incorrect current password" in wrong_curr.json()["message"]

    # 4. Successful change password
    change_resp = client.post(
        "/auth/change-password",
        json={"currentPassword": "TempPass123!", "newPassword": "NewStrongPass1!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert change_resp.status_code == status.HTTP_200_OK
    assert change_resp.json()["message"] == "Password changed successfully"

    # 5. Database flag must_change_password is now False
    db.refresh(user)
    assert user.must_change_password is False

    # 6. User can now access customer accounts with existing session token
    accounts_after = client.get(
        "/accounts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert accounts_after.status_code == status.HTTP_200_OK

    # 7. Relogin with new password returns mustChangePassword=False
    relogin_resp = client.post(
        "/auth/login",
        json={"username": "temp-cust-33", "password": "NewStrongPass1!"},
    )
    assert relogin_resp.status_code == status.HTTP_200_OK
    assert relogin_resp.json()["mustChangePassword"] is False

    # 8. Relogin with old password fails
    old_login = client.post(
        "/auth/login",
        json={"username": "temp-cust-33", "password": "TempPass123!"},
    )
    assert old_login.status_code == status.HTTP_401_UNAUTHORIZED
