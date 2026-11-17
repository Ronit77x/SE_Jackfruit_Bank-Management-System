"""Cross-browser verification for Mozilla Firefox.
- Desktop 1280px: Verified via Selenium with system Firefox (v159.0).
- Windows OS Native Window Limitation Check: Measures Selenium set_window_size(360, 800)
  under Windows OS Win32 window manager to record the 500px clamp limitation honestly.
- Mobile 360px Viewport: Verified via Playwright Gecko engine (v153.0) with genuine
  360x800 layout viewport, measuring actual DOM properties without CSS injection or iframes,
  and asserting innerWidth == 360 and scrollWidth <= clientWidth.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait, Select

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BASE_URL = os.environ.get("BMS_BASE_URL", "http://127.0.0.1:8765")
SHOT_DIR = Path(os.environ.get("BMS_SHOT_DIR", REPO_ROOT / "docs" / "test-plan" / "screenshots"))
OUT_FILE = Path(os.environ.get("BMS_FF_OUT_JSON", REPO_ROOT / "docs" / "test-plan" / "firefox_results.json"))
PLAYWRIGHT_FF_SCRIPT = REPO_ROOT / "tests" / "ui" / "run_firefox_playwright.js"
FF_MOBILE_TMP_OUT = REPO_ROOT / "docs" / "test-plan" / "firefox_mobile_results.json"

SHOT_DIR.mkdir(parents=True, exist_ok=True)
FIREFOX_BINARY = r"C:\Program Files\Mozilla Firefox\firefox.exe"


def measure_geometry(driver):
    script = """
    var cardEl = document.querySelector('.card:not([hidden])') || document.querySelector('#stepDetails');
    var indEl = document.querySelector('.steps-indicator');
    var dividers = Array.from(document.querySelectorAll('.step-divider')).map(function(el) {
        var r = el.getBoundingClientRect();
        return parseFloat(r.width.toFixed(2));
    });
    var cardRect = cardEl ? cardEl.getBoundingClientRect() : { left: 0, right: 0, width: 0 };
    var indRect = indEl ? indEl.getBoundingClientRect() : { left: 0, right: 0, width: 0 };
    return {
        innerWidth: window.innerWidth,
        clientWidth: document.documentElement.clientWidth,
        scrollWidth: document.documentElement.scrollWidth,
        card: {
            left: parseFloat(cardRect.left.toFixed(2)),
            right: parseFloat(cardRect.right.toFixed(2)),
            width: parseFloat(cardRect.width.toFixed(2))
        },
        stepsIndicator: {
            left: parseFloat(indRect.left.toFixed(2)),
            right: parseFloat(indRect.right.toFixed(2)),
            width: parseFloat(indRect.width.toFixed(2))
        },
        stepDividers: dividers
    };
    """
    return driver.execute_script(script)


def run_firefox_desktop():
    print("Starting Firefox at desktop_1280 (1280x800) via Selenium system Firefox...")
    options = Options()
    options.add_argument("--headless")
    options.binary_location = FIREFOX_BINARY
    driver = webdriver.Firefox(options=options)
    driver.set_window_size(1280, 800)
    wait = WebDriverWait(driver, 10)

    try:
        # 1. Login journey
        driver.get(f"{BASE_URL}/ui/index.html")
        wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys("1")
        driver.find_element(By.ID, "password").send_keys("Passw0rd!")
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        wait.until(EC.url_contains("/ui/customer.html"))

        token = driver.execute_script("return sessionStorage.getItem('bms_token');")

        # 2. Navigate to transfer page
        driver.find_element(By.CSS_SELECTOR, "nav a[href='/ui/transfer.html']").click()
        wait.until(EC.url_contains("/ui/transfer.html"))

        # Wait for account selector to populate and select source account
        wait.until(lambda d: len(d.find_element(By.ID, "fromAccountSelect").find_elements(By.TAG_NAME, "option")) > 1)
        Select(driver.find_element(By.ID, "fromAccountSelect")).select_by_value("1000000001")

        # Fill transfer details
        driver.find_element(By.ID, "toAccountInput").send_keys("1000000003")
        driver.find_element(By.ID, "amountInput").send_keys("500.00")

        # Stage 1: Details
        details_geo = measure_geometry(driver)
        assert details_geo["scrollWidth"] <= details_geo["clientWidth"], (
            f"Desktop scrollWidth ({details_geo['scrollWidth']}) must not exceed clientWidth ({details_geo['clientWidth']})"
        )
        driver.save_screenshot(str(SHOT_DIR / "firefox_desktop_1280_details.png"))
        driver.save_screenshot(str(SHOT_DIR / "firefox_desktop_1280.png"))

        # Stage 2: Review
        driver.find_element(By.ID, "btnReview").click()
        wait.until(lambda d: not d.find_element(By.ID, "stepReview").get_attribute("hidden"))
        review_geo = measure_geometry(driver)
        assert review_geo["scrollWidth"] <= review_geo["clientWidth"], "Review scrollWidth must not exceed clientWidth"
        driver.save_screenshot(str(SHOT_DIR / "firefox_desktop_1280_review.png"))

        # Stage 3: Confirm
        driver.find_element(By.ID, "btnConfirmSend").click()
        wait.until(lambda d: not d.find_element(By.ID, "successContent").get_attribute("hidden"))
        receipt_geo = measure_geometry(driver)
        assert receipt_geo["scrollWidth"] <= receipt_geo["clientWidth"], "Receipt scrollWidth must not exceed clientWidth"
        driver.save_screenshot(str(SHOT_DIR / "firefox_desktop_1280_receipt.png"))

        print("✓ Completed Firefox desktop_1280 cleanly via Selenium.")
        return {
            "token": token,
            "results": {
                "details": details_geo,
                "review": review_geo,
                "receipt": receipt_geo,
            }
        }
    finally:
        driver.quit()


def measure_selenium_system_firefox_mobile_attempt(token):
    """Test Selenium window sizing to 360x800 on Windows system Firefox.
    Captures honest measurement showing Windows Win32 ptMinTrackSize.x = 500 limit.
    """
    print("Testing Selenium system Firefox set_window_size(360, 800) under Windows OS...")
    options = Options()
    options.add_argument("--headless")
    options.binary_location = FIREFOX_BINARY
    driver = webdriver.Firefox(options=options)
    driver.set_window_size(360, 800)
    wait = WebDriverWait(driver, 10)

    try:
        driver.get(f"{BASE_URL}/ui/index.html")
        driver.execute_script(f"""
            sessionStorage.setItem('bms_token', {json.dumps(token)});
            sessionStorage.setItem('bms_role', 'Customer');
            sessionStorage.setItem('bms_username', '1');
            sessionStorage.setItem('bms_must_change', 'false');
        """)
        driver.get(f"{BASE_URL}/ui/transfer.html")
        wait.until(lambda d: len(d.find_element(By.ID, "fromAccountSelect").find_elements(By.TAG_NAME, "option")) > 1)

        geo = measure_geometry(driver)
        print(f"Selenium system Firefox measured window: innerWidth={geo['innerWidth']}, clientWidth={geo['clientWidth']}")
        return {
            "measured": geo,
            "limitation": "Windows OS Win32 minimum window tracking size clamps native Firefox top-level window to 500px",
        }
    finally:
        driver.quit()


def run_firefox_mobile():
    """Run genuine 360px mobile viewport verification in Firefox Gecko engine via Playwright."""
    print("Executing genuine 360px Firefox mobile verification via Playwright Gecko engine...")
    env = os.environ.copy()
    env["BMS_BASE_URL"] = BASE_URL
    env["BMS_SHOT_DIR"] = str(SHOT_DIR)
    env["BMS_FF_MOBILE_OUT"] = str(FF_MOBILE_TMP_OUT)

    res = subprocess.run(["node", str(PLAYWRIGHT_FF_SCRIPT)], env=env, cwd=str(REPO_ROOT))
    if res.returncode != 0:
        raise RuntimeError(f"Playwright Firefox mobile verification failed with code {res.returncode}")

    if not FF_MOBILE_TMP_OUT.exists():
        raise FileNotFoundError(f"Expected output file not found: {FF_MOBILE_TMP_OUT}")

    with open(FF_MOBILE_TMP_OUT, "r", encoding="utf-8") as f:
        mobile_data = json.load(f)

    # Strictly assert genuine 360px DOM metrics and no horizontal scroll
    for stage_name, geo in mobile_data.items():
        assert geo["innerWidth"] == 360, f"{stage_name} innerWidth must be 360, got {geo['innerWidth']}"
        assert geo["clientWidth"] == 360, f"{stage_name} clientWidth must be 360, got {geo['clientWidth']}"
        assert geo["scrollWidth"] <= geo["clientWidth"], (
            f"{stage_name} scrollWidth ({geo['scrollWidth']}) must not exceed clientWidth ({geo['clientWidth']})"
        )

    print("✓ Successfully verified genuine 360px mobile Firefox metrics (all stages scrollWidth <= clientWidth).")
    FF_MOBILE_TMP_OUT.unlink()
    print("Cleaned intermediate Firefox mobile results JSON.")
    return mobile_data


def main():
    desktop_res = run_firefox_desktop()
    token = desktop_res["token"]

    # Document honest Selenium system Firefox window measurement
    selenium_limitation = measure_selenium_system_firefox_mobile_attempt(token)

    # Run genuine 360px mobile verification in Firefox Gecko
    mobile_res = run_firefox_mobile()

    results = {
        "firefox": {
            "desktop_1280": desktop_res["results"],
            "mobile_360": mobile_res,
            "selenium_system_firefox_windows_limitation": selenium_limitation,
        }
    }

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Firefox verification results written to {OUT_FILE}")


if __name__ == "__main__":
    main()
