"""Master browser verification coordinator for US-15 (TC-UX-02 / BMS-NF-006).

Sets up a clean temporary test database with authentic test customer credentials,
starts the live FastAPI server, and executes genuine browser tests across:
  - Google Chrome (1280px Desktop & 360px Mobile) via Playwright
  - Microsoft Edge (1280px Desktop & 360px Mobile) via Playwright
  - Mozilla Firefox (1280px Desktop & 360px Mobile) via Selenium

Captures fresh screenshots and compiles complete layout geometry into:
  docs/test-plan/browser_verification_results.json
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from decimal import Decimal
from pathlib import Path
import urllib.request

from cryptography.fernet import Fernet

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

PORT = 8765
BASE_URL = f"http://127.0.0.1:{PORT}"
SHOT_DIR = REPO_ROOT / "docs" / "test-plan" / "screenshots"
RESULTS_JSON = REPO_ROOT / "docs" / "test-plan" / "browser_verification_results.json"


def setup_test_db(temp_dir):
    db_file = Path(temp_dir) / "test_browsers.db"
    db_url = f"sqlite:///{db_file.resolve()}"
    data_key = Fernet.generate_key().decode()

    os.environ["BMS_DATABASE_URL"] = db_url
    os.environ["BMS_DATA_KEY"] = data_key

    from app.database import Base, engine, SessionLocal
    from app.security import hash_password
    from tests.factories import create_account, create_customer, create_user

    Base.metadata.create_all(engine)

    with SessionLocal() as db:
        # Customer 1: Asha Rao (username 1, password Passw0rd!)
        c1 = create_customer(db, name="Asha Rao", phone="9876543210", email="asha@example.com")
        u1 = create_user(db, customer=c1, username="1", password_hash=hash_password("Passw0rd!"))
        a1 = create_account(
            db, customer=c1, account_number="1000000001", type="Savings", balance=Decimal("10000.00"), status="Active"
        )
        a2 = create_account(
            db, customer=c1, account_number="1000000002", type="Current", balance=Decimal("25000.00"), status="Active"
        )
        a_frozen = create_account(
            db, customer=c1, account_number="1000000099", type="Savings", balance=Decimal("2000.00"), status="Frozen"
        )

        # Customer 2: Ravi Kumar (username 2, password Passw0rd!, recipient 1000000003)
        c2 = create_customer(db, name="Ravi Kumar", phone="9876543211", email="ravi@example.com")
        u2 = create_user(db, customer=c2, username="2", password_hash=hash_password("Passw0rd!"))
        a3 = create_account(
            db, customer=c2, account_number="1000000003", type="Savings", balance=Decimal("15000.00"), status="Active"
        )
        db.commit()

    print(f"Test database initialized with Customer 1 (accounts 1000000001, 1000000002) and recipient 1000000003.")


def wait_for_server(url, timeout=15):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(f"{url}/ui/index.html") as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def main():
    temp_dir = tempfile.mkdtemp(prefix="bms_browser_test_")
    server_proc = None

    try:
        setup_test_db(temp_dir)

        print(f"Starting background FastAPI development server on port {PORT}...")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        server_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT), "--log-level", "warning"],
            env=env,
            cwd=str(REPO_ROOT),
        )

        if not wait_for_server(BASE_URL):
            raise RuntimeError(f"Server failed to start on {BASE_URL} within timeout")
        print(f"FastAPI server is active and serving at {BASE_URL}")

        os.environ["BMS_BASE_URL"] = BASE_URL
        os.environ["BMS_SHOT_DIR"] = str(SHOT_DIR)

        # 1. Run Playwright verification (Chrome & Edge)
        pw_out = REPO_ROOT / "docs" / "test-plan" / "playwright_results.json"
        os.environ["BMS_OUT_JSON"] = str(pw_out)
        print("\n--- Running Chrome and Edge verification via Playwright ---")
        res_pw = subprocess.run(["node", str(REPO_ROOT / "tests" / "ui" / "run_browser_playwright.js")], env=os.environ, cwd=str(REPO_ROOT))
        if res_pw.returncode != 0:
            raise RuntimeError(f"Playwright browser verification failed with exit code {res_pw.returncode}")

        # 2. Run Selenium verification (Firefox)
        ff_out = REPO_ROOT / "docs" / "test-plan" / "firefox_results.json"
        os.environ["BMS_FF_OUT_JSON"] = str(ff_out)
        print("\n--- Running Firefox verification via Selenium ---")
        res_ff = subprocess.run([sys.executable, str(REPO_ROOT / "tests" / "ui" / "run_browser_firefox.py")], env=os.environ, cwd=str(REPO_ROOT))
        if res_ff.returncode != 0:
            raise RuntimeError(f"Firefox browser verification failed with exit code {res_ff.returncode}")

        # 3. Merge results into docs/test-plan/browser_verification_results.json
        with open(pw_out, "r", encoding="utf-8") as f:
            pw_data = json.load(f)
        with open(ff_out, "r", encoding="utf-8") as f:
            ff_data = json.load(f)

        combined = {}
        combined.update(pw_data)
        combined.update(ff_data)

        with open(RESULTS_JSON, "w", encoding="utf-8") as f:
            json.dump(combined, f, indent=2)

        print(f"\n✓ Successfully compiled all 6 browser/viewport results into {RESULTS_JSON}")

        # Clean up temporary JSON files
        if pw_out.exists():
            pw_out.unlink()
        if ff_out.exists():
            ff_out.unlink()

    finally:
        if server_proc:
            print("Stopping FastAPI test server...")
            server_proc.terminate()
            try:
                server_proc.wait(timeout=5)
            except Exception:
                server_proc.kill()
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("Cleaned up disposable database environment.")


if __name__ == "__main__":
    main()
