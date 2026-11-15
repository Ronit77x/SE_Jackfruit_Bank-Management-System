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
    assert 'id="logout-btn"' in resp.text


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


def test_mandatory_reset_banner_css_and_attributes(client):
    """Verify that CSS enforces hidden elements with display: none !important, and that

    the banner has the hidden attribute without the 'show' class in initial HTML.
    """
    css_resp = client.get("/ui/css/style.css")
    assert css_resp.status_code == status.HTTP_200_OK
    assert "[hidden]" in css_resp.text
    assert "display: none !important" in css_resp.text

    html_resp = client.get("/ui/change-password.html")
    assert html_resp.status_code == status.HTTP_200_OK
    assert 'id="mandatory-notice"' in html_resp.text
    assert 'class="message error"' in html_resp.text
    assert 'class="message show error"' not in html_resp.text


def test_navigation_destinations_for_all_roles(client):
    """Verify that Customer and Teller destinations exist and return 200 OK,

    and verify that /ui/admin.html returns 404 while change-password.html keeps Admin
    on the page with a working logout action rather than redirecting to /docs or /ui/admin.html.
    """
    # Customer destination
    cust_resp = client.get("/ui/customer.html")
    assert cust_resp.status_code == status.HTTP_200_OK

    # Teller destination
    teller_resp = client.get("/ui/teller-cash.html")
    assert teller_resp.status_code == status.HTTP_200_OK

    # Verify obsolete admin.html returns 404 (not invented or present)
    obsolete_admin = client.get("/ui/admin.html")
    assert obsolete_admin.status_code == status.HTTP_404_NOT_FOUND

    # Verify change-password page contains the role-aware handling without Admin redirects
    html_resp = client.get("/ui/change-password.html")
    assert 'if (role === "Admin" || !dest)' in html_resp.text
    assert 'continueBtn.setAttribute("hidden", "")' in html_resp.text
    assert 'logoutBtn.removeAttribute("hidden")' in html_resp.text


def test_admin_mandatory_reset_flow(client, db):
    """Verify mandatory reset and logout flow for an Admin user."""
    admin_user = create_user(
        db,
        username="temp-admin-33",
        role="Admin",
        password_hash=hash_password("TempAdmin123!"),
        must_change_password=True,
    )

    # 1. Login returns mustChangePassword=True
    login_resp = client.post(
        "/auth/login",
        json={"username": "temp-admin-33", "password": "TempAdmin123!"},
    )
    assert login_resp.status_code == status.HTTP_200_OK
    token = login_resp.json()["token"]
    assert login_resp.json()["mustChangePassword"] is True

    # 2. Change password
    change_resp = client.post(
        "/auth/change-password",
        json={"currentPassword": "TempAdmin123!", "newPassword": "NewAdminStrong1!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert change_resp.status_code == status.HTTP_200_OK
    assert change_resp.json()["message"] == "Password changed successfully"

    # 3. must_change_password is False in DB
    db.refresh(admin_user)
    assert admin_user.must_change_password is False

    # 4. Admin logout endpoint works and terminates session
    logout_resp = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_resp.status_code == status.HTTP_200_OK

    # 5. Old token is now invalidated
    after_logout = client.get(
        "/admin/audit-logs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert after_logout.status_code == status.HTTP_401_UNAUTHORIZED

    # 6. Relogin works with new password and mustChangePassword is False
    relogin_resp = client.post(
        "/auth/login",
        json={"username": "temp-admin-33", "password": "NewAdminStrong1!"},
    )
    assert relogin_resp.status_code == status.HTTP_200_OK
    assert relogin_resp.json()["mustChangePassword"] is False
