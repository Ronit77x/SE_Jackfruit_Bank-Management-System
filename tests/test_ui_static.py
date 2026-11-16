"""The browser pages are served by the application at /ui (BMS-NF-006 groundwork)."""
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "app" / "static"


def test_login_page_is_served(client):
    response = client.get("/ui/index.html")
    assert response.status_code == 200
    assert "Bank Management System" in response.text
    assert 'name="viewport"' in response.text  # responsive layout


def test_shared_files_are_served(client):
    assert client.get("/ui/css/style.css").status_code == 200
    assert "bms" in client.get("/ui/js/api.js").text
    assert client.get("/ui/teller-cash.html").status_code == 200


def test_root_redirects_to_the_login_page(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/ui/index.html"


def test_every_page_has_the_responsive_meta_tag_and_shared_scripts():
    for page in STATIC.glob("*.html"):
        text = page.read_text(encoding="utf-8")
        assert 'name="viewport"' in text, page.name
        assert "/ui/css/style.css" in text, page.name
        assert "/ui/js/api.js" in text, page.name


def test_css_declares_narrow_screen_and_table_overflow_rules():
    """Source-level check only; rendered browser/viewport verification is separate."""
    css = (STATIC / "css" / "style.css").read_text(encoding="utf-8")
    assert "max-width: 400px" in css and "overflow-x: auto" in css
