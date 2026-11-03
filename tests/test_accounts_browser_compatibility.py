"""Automated tests for US-15: Browser Compatibility & Responsive UI (BMS-NF-006, TC-UX-02).

Owner: Member 2 (Vijay Kumar).
"""

from pathlib import Path
import pytest
from app.routers.accounts import FRONTEND_TRANSFER_HTML


@pytest.fixture()
def transfer_html_content():
    """Load the raw transfer.html content."""
    assert FRONTEND_TRANSFER_HTML.exists(), "frontend/transfer.html must exist"
    return FRONTEND_TRANSFER_HTML.read_text(encoding="utf-8")


def test_html_contains_viewport_meta_tag(transfer_html_content):
    """BMS-NF-006: Viewport meta tag must be present with proper scale configuration."""
    assert '<meta name="viewport"' in transfer_html_content
    assert 'content="width=device-width, initial-scale=1.0"' in transfer_html_content


def test_html_cross_browser_input_number_normalization(transfer_html_content):
    """TC-UX-02: Ensure number spin buttons are normalized across Firefox and Chromium."""
    assert "-moz-appearance: textfield" in transfer_html_content
    assert "-webkit-outer-spin-button" in transfer_html_content
    assert "-webkit-inner-spin-button" in transfer_html_content


def test_html_responsive_media_queries(transfer_html_content):
    """BMS-NF-006: Ensure media queries exist for mobile down to 360px viewport."""
    assert "@media (max-width: 480px)" in transfer_html_content
    assert "@media (max-width: 380px)" in transfer_html_content
    assert ".step-divider" in transfer_html_content
    assert ".step-item" in transfer_html_content
    assert ".btn-group" in transfer_html_content


def test_html_print_media_query_for_receipts(transfer_html_content):
    """TC-UX-02: Verify print stylesheet is configured to hide navigation and buttons."""
    assert "@media print" in transfer_html_content
    assert "display: none !important" in transfer_html_content


def test_html_accessible_form_attributes(transfer_html_content):
    """Ensure standard accessibility, semantic labels, and numeric input modes are configured."""
    assert 'for="fromAccountSelect"' in transfer_html_content
    assert 'for="toAccountInput"' in transfer_html_content
    assert 'for="amountInput"' in transfer_html_content
    assert 'inputmode="numeric"' in transfer_html_content
    assert 'pattern="[0-9]{10}"' in transfer_html_content
    assert 'role="alert"' in transfer_html_content


def test_html_no_deprecated_browser_apis(transfer_html_content):
    """Verify standards compliance: no legacy IE/proprietary APIs are used."""
    deprecated = [
        "document.all",
        "attachEvent",
        "ActiveXObject",
        "window.event",
        "document.layers",
    ]
    for api in deprecated:
        assert api not in transfer_html_content, f"Deprecated API '{api}' found in frontend"


def test_html_uses_standard_cross_browser_apis(transfer_html_content):
    """Verify standard ECMAScript and Web APIs used across Chrome, Edge, and Firefox."""
    assert "sessionStorage" in transfer_html_content
    assert "fetch(" in transfer_html_content
    assert "addEventListener" in transfer_html_content
    assert "document.getElementById" in transfer_html_content


def test_transfer_endpoint_serves_responsive_html(client):
    """Verify GET /transfer serves the page with proper HTML content type."""
    response = client.get("/transfer")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "viewport" in response.text
    assert "@media (max-width: 480px)" in response.text
