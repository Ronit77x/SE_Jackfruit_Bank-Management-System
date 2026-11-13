"""Automated source-level and HTTP contract tests for US-15: Browser Compatibility & Responsive UI (BMS-NF-006, TC-UX-02).

Owner: Member 2 (Vijay Kumar).

NOTE ON SCOPE:
These tests verify static HTML structure, CSS rules, meta tags, and HTTP response
headers via FastAPI TestClient. They verify that the required responsive declarations,
cross-browser CSS properties, accessibility attributes, and API endpoints are present
in the served code. They do NOT measure rendered pixel layout in a browser engine.
Rendered browser measurements (scrollWidth, clientWidth, screenshot artifacts) are
conducted with real browser binaries and documented in docs/test-plan/TC-UX-02-browser-compatibility.md.
"""

from pathlib import Path
import pytest
from app.routers.accounts import FRONTEND_TRANSFER_HTML


@pytest.fixture()
def transfer_html_content():
    """Load the raw transfer.html content."""
    assert FRONTEND_TRANSFER_HTML.exists(), "frontend/transfer.html must exist"
    return FRONTEND_TRANSFER_HTML.read_text(encoding="utf-8")


def test_html_source_declares_viewport_meta_tag(transfer_html_content):
    """BMS-NF-006 (Source check): Viewport meta tag must be declared with proper scale configuration."""
    assert '<meta name="viewport"' in transfer_html_content
    assert 'content="width=device-width, initial-scale=1.0"' in transfer_html_content


def test_html_source_normalizes_cross_browser_input_number(transfer_html_content):
    """TC-UX-02 (Source check): CSS rules must normalize number spin buttons for Firefox and Chromium."""
    assert "-moz-appearance: textfield" in transfer_html_content
    assert "-webkit-outer-spin-button" in transfer_html_content
    assert "-webkit-inner-spin-button" in transfer_html_content


def test_html_source_defines_responsive_media_queries(transfer_html_content):
    """BMS-NF-006 (Source check): CSS media queries must exist for responsive scaling down to 360px."""
    assert "@media (max-width: 480px)" in transfer_html_content
    assert "@media (max-width: 380px)" in transfer_html_content
    assert ".step-divider" in transfer_html_content
    assert ".step-item" in transfer_html_content
    assert ".btn-group" in transfer_html_content


def test_html_source_defines_print_stylesheet_for_receipts(transfer_html_content):
    """TC-UX-02 (Source check): Print CSS must hide navigation and buttons for clean receipt printing."""
    assert "@media print" in transfer_html_content
    assert "display: none !important" in transfer_html_content


def test_html_source_has_accessible_form_attributes(transfer_html_content):
    """Source check: Semantic labels, numeric input modes, and ARIA attributes must be declared."""
    assert 'for="fromAccountSelect"' in transfer_html_content
    assert 'for="toAccountInput"' in transfer_html_content
    assert 'for="amountInput"' in transfer_html_content
    assert 'inputmode="numeric"' in transfer_html_content
    assert 'pattern="[0-9]{10}"' in transfer_html_content
    assert 'role="alert"' in transfer_html_content


def test_html_source_excludes_legacy_proprietary_apis(transfer_html_content):
    """Source check: No legacy IE or obsolete browser APIs are present."""
    deprecated = [
        "document.all",
        "attachEvent",
        "ActiveXObject",
        "window.event",
        "document.layers",
    ]
    for api in deprecated:
        assert api not in transfer_html_content, f"Deprecated API '{api}' found in frontend"


def test_html_source_uses_standard_cross_browser_apis(transfer_html_content):
    """Source check: Uses standard ECMAScript and Web APIs supported across modern browsers."""
    assert "sessionStorage" in transfer_html_content
    assert "fetch(" in transfer_html_content
    assert "addEventListener" in transfer_html_content
    assert "document.getElementById" in transfer_html_content


def test_transfer_endpoint_serves_html_with_responsive_headers(client):
    """HTTP check: GET /transfer serves HTML content type with responsive markup."""
    response = client.get("/transfer")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "viewport" in response.text
    assert "@media (max-width: 480px)" in response.text
