"""Reproduce US-27 checks against an isolated local BMS HTTPS instance.

Run from the repository root:
    python -m scripts.verify_local_https

The verifier uses a throwaway SQLite database, Fernet key, and self-signed
certificate. It does not touch the normal bms.db or print credentials, tokens,
certificate material, account numbers, or personal identifiers.
"""
from __future__ import annotations

import ipaddress
import json
import os
import platform
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import uvicorn
from cryptography import x509
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from sqlalchemy import select


def _make_certificate(directory: Path) -> tuple[Path, Path]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                ]
            ),
            critical=False,
        )
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    cert_path = directory / "cert.pem"
    key_path = directory / "key.pem"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    return cert_path, key_path


def _commit_info() -> tuple[str, str]:
    """Identify the tested source revision and how it was obtained."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip(), "git rev-parse HEAD"
    except (OSError, subprocess.SubprocessError):
        return os.environ.get("GITHUB_SHA", "unavailable"), "GITHUB_SHA environment fallback"


def _check_tls_versions(port: int, cert_path: Path) -> dict[str, str]:
    checks: dict[str, str] = {}
    for name, version in (
        ("TLS1.2", ssl.TLSVersion.TLSv1_2),
        ("TLS1.3", ssl.TLSVersion.TLSv1_3),
    ):
        context = ssl.create_default_context(cafile=str(cert_path))
        context.minimum_version = version
        context.maximum_version = version
        with socket.create_connection(("127.0.0.1", port), timeout=5) as raw:
            with context.wrap_socket(raw, server_hostname="localhost") as secure:
                checks[name] = secure.version() or "unknown"
        assert checks[name] == name.replace("TLS", "TLSv")

    for name, version in (
        ("TLS1.0", ssl.TLSVersion.TLSv1),
        ("TLS1.1", ssl.TLSVersion.TLSv1_1),
    ):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            context.minimum_version = version
            context.maximum_version = version
            context.set_ciphers("ALL:@SECLEVEL=0")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=5) as raw:
                with context.wrap_socket(raw, server_hostname="localhost"):
                    raise AssertionError(f"{name} was unexpectedly accepted")
        except ssl.SSLError as error:
            # These are server-side refusal/close outcomes; local no-cipher errors
            # are intentionally not accepted as proof of server-side rejection.
            allowed_reasons = {
                "TLSV1_ALERT_PROTOCOL_VERSION",
                "UNSUPPORTED_PROTOCOL",
                "UNEXPECTED_EOF_WHILE_READING",
            }
            if error.reason not in allowed_reasons:
                raise
            checks[name] = "refused: " + error.reason
    return checks


def main() -> None:
    started_at = datetime.now(timezone.utc).isoformat()
    with tempfile.TemporaryDirectory(prefix="bms-local-https-") as temporary:
        directory = Path(temporary)
        # Set these before importing application/database modules.
        os.environ["BMS_DATABASE_URL"] = (
            "sqlite:///" + (directory / "verification.db").as_posix()
        )
        os.environ["BMS_DATA_KEY"] = Fernet.generate_key().decode("ascii")

        cert_path, key_path = _make_certificate(directory)

        from app.database import Base, SessionLocal, engine
        from app.models import Account
        from scripts.seed import seed

        Base.metadata.create_all(engine)
        with SessionLocal() as db:
            seed(db)
            source = db.scalar(
                select(Account).where(Account.customer_id == 1).order_by(Account.id)
            )
            destination = db.scalar(
                select(Account).where(Account.customer_id != 1).order_by(Account.id)
            )
            if source is None or destination is None:
                raise RuntimeError("Seed data did not create transfer test accounts")
            source_number = source.account_number
            destination_number = destination.account_number

        config = uvicorn.Config(
            "app.main:app",
            host="127.0.0.1",
            port=0,
            ssl_certfile=str(cert_path),
            ssl_keyfile=str(key_path),
            ssl_version=ssl.PROTOCOL_TLS_SERVER,
            log_level="error",
        )
        config.load()
        config.ssl.minimum_version = ssl.TLSVersion.TLSv1_2

        server = uvicorn.Server(config)
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        worker = threading.Thread(
            target=server.run,
            kwargs={"sockets": [listener]},
            daemon=True,
        )
        checks: dict[str, int | str] = {}

        try:
            worker.start()
            deadline = time.monotonic() + 15
            while not server.started and worker.is_alive() and time.monotonic() < deadline:
                time.sleep(0.05)
            if not server.started:
                raise RuntimeError("Temporary HTTPS server did not start")

            checks.update(_check_tls_versions(port, cert_path))

            # Explicitly trust only this ephemeral certificate. The SAN matches
            # 127.0.0.1, so httpx verifies both its chain and hostname/IP identity.
            trust = ssl.create_default_context(cafile=str(cert_path))
            with httpx.Client(
                base_url=f"https://127.0.0.1:{port}", verify=trust, timeout=10
            ) as client:
                for path in ("/health", "/docs"):
                    checks[path] = client.get(path).status_code
                    assert checks[path] == 200

                checks["missing_login"] = client.get("/accounts").status_code
                assert checks["missing_login"] == 401

                response = client.post(
                    "/auth/login",
                    json={"username": "teller1", "password": "Passw0rd!"},
                )
                assert response.status_code == 200
                teller_headers = {
                    "Authorization": "Bearer " + response.json()["token"]
                }

                response = client.post(
                    "/accounts",
                    headers=teller_headers,
                    json={
                        "account_type": "Savings",
                        "deposit": "1000",
                        "name": "HTTPS Test",
                        "date_of_birth": "2000-01-01",
                        "address": "Test",
                        "phone": "9999999999",
                        "email": "https@example.com",
                        "id_proof_number": "HTTPS-TEST-ID",
                    },
                )
                checks["account_opening"] = response.status_code
                assert response.status_code == 201
                opened_account = response.json().get("account_number")
                if not opened_account or not opened_account.isascii() or not opened_account.isdigit():
                    raise AssertionError("Account opening did not return a valid account number")

                checks["deposit"] = client.post(
                    "/transactions/deposit",
                    headers=teller_headers,
                    json={"accountId": opened_account, "amount": "10"},
                ).status_code
                checks["withdrawal"] = client.post(
                    "/transactions/withdraw",
                    headers=teller_headers,
                    json={"accountId": opened_account, "amount": "10"},
                ).status_code
                assert checks["deposit"] == checks["withdrawal"] == 201

                response = client.post(
                    "/auth/login",
                    json={"username": "1", "password": "Passw0rd!"},
                )
                assert response.status_code == 200
                customer_headers = {
                    "Authorization": "Bearer " + response.json()["token"]
                }
                checks["own_accounts"] = client.get(
                    "/accounts", headers=customer_headers
                ).status_code
                assert checks["own_accounts"] == 200

                checks["transfer"] = client.post(
                    "/transactions/transfer",
                    headers=customer_headers,
                    json={
                        "fromAccount": source_number,
                        "toAccount": destination_number,
                        "amount": "10",
                    },
                ).status_code
                assert checks["transfer"] == 201

            revision_sha, revision_source = _commit_info()
            result = {
                "result": "passed",
                "tested_at_utc": started_at,
                "source_revision_sha": revision_sha,
                "source_revision_source": revision_source,
                "is_git_worktree": Path(".git").exists(),
                "python": sys.version.split()[0],
                "openssl": ssl.OPENSSL_VERSION,
                "platform": platform.platform(),
                "server": "local Uvicorn HTTPS; loopback only",
                "certificate_validation": (
                    "temporary certificate explicitly trusted; SAN/IP hostname verification enabled"
                ),
                "checks": checks,
                "scope_note": (
                    "This verifies the temporary local Uvicorn HTTPS server only; "
                    "it does not verify a deployed Nginx reverse proxy or public-CA certificate."
                ),
            }
            print(json.dumps(result, indent=2))
        finally:
            server.should_exit = True
            worker.join(timeout=10)
            listener.close()
            engine.dispose()
            if worker.is_alive():
                raise RuntimeError("Temporary HTTPS server did not stop")


if __name__ == "__main__":
    main()
