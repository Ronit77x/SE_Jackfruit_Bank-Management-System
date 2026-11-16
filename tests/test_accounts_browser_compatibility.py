"""Automated source-level and HTTP contract tests for US-15: Browser Compatibility & Responsive UI (BMS-NF-006, TC-UX-02).

Owner: Member 2 (Vijay Kumar).

NOTE ON SCOPE:
These tests verify both the canonical application implementation (app/static/transfer.html,
app/static/css/transfer.css, app/static/js/transfer.js) and legacy route compatibility via FastAPI TestClient.
They verify that required responsive declarations, cross-browser CSS properties, accessibility attributes,
and static/API endpoints are served correctly. Rendered browser measurements and visual screenshots across
Chrome, Edge, and Firefox binaries are conducted and documented in docs/test-plan/TC-UX-02-browser-compatibility.md.
"""

from pathlib import Path
import pytest
from app.routers.accounts import FRONTEND_TRANSFER_HTML, STATIC_TRANSFER_HTML

STATIC_CSS_TRANSFER = Path(__file__).resolve().parent.parent / "app" / "static" / "css" / "transfer.css"
STATIC_JS_TRANSFER = Path(__file__).resolve().parent.parent / "app" / "static" / "js" / "transfer.js"
STATIC_JS_API = Path(__file__).resolve().parent.parent / "app" / "static" / "js" / "api.js"


@pytest.fixture()
def canonical_transfer_html():
    """Load canonical transfer.html markup."""
    assert STATIC_TRANSFER_HTML.exists(), "app/static/transfer.html must exist as canonical UI"
    return STATIC_TRANSFER_HTML.read_text(encoding="utf-8")


@pytest.fixture()
def canonical_transfer_css():
    """Load canonical transfer.css stylesheet."""
    assert STATIC_CSS_TRANSFER.exists(), "app/static/css/transfer.css must exist"
    return STATIC_CSS_TRANSFER.read_text(encoding="utf-8")


@pytest.fixture()
def canonical_transfer_js():
    """Load canonical transfer.js and api.js scripts."""
    assert STATIC_JS_TRANSFER.exists(), "app/static/js/transfer.js must exist"
    assert STATIC_JS_API.exists(), "app/static/js/api.js must exist"
    return STATIC_JS_TRANSFER.read_text(encoding="utf-8") + "\n" + STATIC_JS_API.read_text(encoding="utf-8")


@pytest.fixture()
def legacy_transfer_html():
    """Load legacy frontend/transfer.html content if present for backward compatibility checks."""
    if FRONTEND_TRANSFER_HTML.exists():
        return FRONTEND_TRANSFER_HTML.read_text(encoding="utf-8")
    return None


# ---------------------------------------------------------------------------
# Canonical Application Verification (app/static/transfer.html, css, js)
# ---------------------------------------------------------------------------

def test_canonical_html_declares_viewport_meta_tag(canonical_transfer_html):
    """BMS-NF-006: Canonical transfer UI declares proper mobile viewport configuration."""
    assert '<meta name="viewport"' in canonical_transfer_html
    assert 'content="width=device-width, initial-scale=1.0"' in canonical_transfer_html


def test_canonical_css_normalizes_cross_browser_input_number(canonical_transfer_css):
    """TC-UX-02: Canonical CSS normalizes numeric spin buttons across Blink and Gecko engines."""
    assert "-moz-appearance: textfield" in canonical_transfer_css
    assert "-webkit-outer-spin-button" in canonical_transfer_css
    assert "-webkit-inner-spin-button" in canonical_transfer_css


def test_canonical_css_defines_responsive_media_queries(canonical_transfer_css):
    """BMS-NF-006: Canonical CSS defines responsive breakpoints for scaling down to 360px benchmark."""
    assert "@media (max-width: 480px)" in canonical_transfer_css
    assert "@media (max-width: 380px)" in canonical_transfer_css
    assert ".step-divider" in canonical_transfer_css
    assert ".step-item" in canonical_transfer_css
    assert ".btn-group" in canonical_transfer_css


def test_canonical_css_defines_print_stylesheet_for_receipts(canonical_transfer_css):
    """TC-UX-02: Canonical CSS defines print media query to produce clean receipt printouts."""
    assert "@media print" in canonical_transfer_css
    assert "display: none !important" in canonical_transfer_css


def test_canonical_html_has_accessible_form_attributes(canonical_transfer_html):
    """TC-UX-02: Form controls provide semantic labels, numeric input mode, patterns, and ARIA roles."""
    assert 'for="fromAccountSelect"' in canonical_transfer_html
    assert 'for="toAccountInput"' in canonical_transfer_html
    assert 'for="amountInput"' in canonical_transfer_html
    assert 'inputmode="numeric"' in canonical_transfer_html
    assert 'pattern="[0-9]{10}"' in canonical_transfer_html
    assert 'role="alert"' in canonical_transfer_html


def test_canonical_js_excludes_legacy_proprietary_apis(canonical_transfer_js):
    """BMS-NF-006: Canonical client code avoids deprecated or non-standard browser APIs."""
    deprecated = [
        "document.all",
        "attachEvent",
        "ActiveXObject",
        "window.event",
        "document.layers",
    ]
    for api in deprecated:
        assert api not in canonical_transfer_js, f"Deprecated API '{api}' found in client JS"


def test_canonical_js_uses_standard_cross_browser_apis(canonical_transfer_js):
    """BMS-NF-006: Client code relies exclusively on standard ECMAScript and HTML5 DOM APIs."""
    assert "sessionStorage" in canonical_transfer_js
    assert "fetch(" in canonical_transfer_js
    assert "addEventListener" in canonical_transfer_js
    assert "document.getElementById" in canonical_transfer_js


# ---------------------------------------------------------------------------
# HTTP Serving Endpoints (GET /transfer, GET /ui/transfer.html, GET /ui/css/transfer.css)
# ---------------------------------------------------------------------------

def test_transfer_endpoint_serves_canonical_html(client):
    """HTTP check: GET /transfer serves canonical transfer HTML referencing modular assets."""
    response = client.get("/transfer")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "viewport" in response.text
    assert "/ui/css/transfer.css" in response.text
    assert "/ui/js/transfer.js" in response.text


def test_static_transfer_html_endpoint(client):
    """HTTP check: GET /ui/transfer.html serves 200 OK with proper markup."""
    response = client.get("/ui/transfer.html")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Transfer Money" in response.text


def test_static_transfer_css_endpoint_serves_responsive_rules(client):
    """HTTP check: GET /ui/css/transfer.css serves stylesheet with responsive and cross-browser rules."""
    response = client.get("/ui/css/transfer.css")
    assert response.status_code == 200
    assert "text/css" in response.headers.get("content-type", "")
    css_text = response.text
    assert "-moz-appearance: textfield" in css_text
    assert "-webkit-outer-spin-button" in css_text
    assert "@media (max-width: 480px)" in css_text
    assert "@media (max-width: 380px)" in css_text
    assert "@media print" in css_text


# ---------------------------------------------------------------------------
# Legacy Backward Compatibility
# ---------------------------------------------------------------------------

def test_legacy_transfer_html_retains_compatibility(legacy_transfer_html):
    """Retain compatibility check for legacy frontend/transfer.html if retained in workspace."""
    if legacy_transfer_html is None:
        pytest.skip("frontend/transfer.html not present")
    assert '<meta name="viewport"' in legacy_transfer_html
    assert "-moz-appearance: textfield" in legacy_transfer_html
    assert "@media (max-width: 480px)" in legacy_transfer_html
