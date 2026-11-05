"""No page may put server or user text into the page as HTML (BMS-SR-005, cross-site scripting).

Use textContent or the helpers bms.el(...) / bms.clear(...) from app/static/js/api.js instead.
This test checks every file under app/static, including pages added by other team members.
"""
import re
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "app" / "static"
FORBIDDEN = [r"\.innerHTML", r"\.outerHTML", r"insertAdjacentHTML", r"document\.write", r"\beval\(", r"new Function\("]


def test_no_unsafe_html_insertion_anywhere_in_the_ui():
    problems = []
    for path in list(STATIC.rglob("*.html")) + list(STATIC.rglob("*.js")):
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN:
            if re.search(pattern, text):
                problems.append(f"{path.relative_to(STATIC)}: {pattern}")
    assert problems == [], "Unsafe HTML insertion found:\n" + "\n".join(problems)


def test_pages_do_not_load_scripts_from_other_sites():
    for path in STATIC.rglob("*.html"):
        for source in re.findall(r'<script[^>]+src="([^"]+)"', path.read_text(encoding="utf-8")):
            assert source.startswith("/ui/"), f"{path.name} loads {source}"
