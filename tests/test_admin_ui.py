from pathlib import Path


STATIC = Path(__file__).resolve().parent.parent / "app" / "static"


def test_admin_page_is_served(client):
    response = client.get("/ui/admin.html")
    assert response.status_code == 200
    assert 'src="/ui/js/admin.js"' in response.text
    assert "Teller management" in response.text
    assert "Audit log" in response.text
    assert "Daily transaction report" in response.text


def test_admin_ui_uses_existing_admin_apis_and_role_guard():
    source = (STATIC / "js" / "admin.js").read_text(encoding="utf-8")
    assert 'bms.requireRole(["Admin"])' in source
    assert '"/admin/users"' in source
    assert '"/admin/audit-logs?' in source
    assert 'name="user_id"' in (STATIC / "admin.html").read_text(encoding="utf-8")
    assert '"/admin/reports/daily?date="' in source
    assert "bms.patch" in source
    assert 'form.elements.namedItem("action").value' in source
    assert "bms.money" in source
