# US-27 security verification

## Input validation

The transaction request models require account identifiers to match exactly ten
ASCII digits, amounts to be positive `Decimal` values with at most two decimal
places, and reject unknown JSON fields. The regression tests exercise SQL
injection-like and script-like values and verify that no transaction or balance
is changed.

## Database access

The transaction service uses SQLAlchemy `select(...).where(...)` expressions;
untrusted account identifiers are bound parameters, not interpolated SQL.

## HTTPS/TLS

`deploy/nginx-https.conf` is a deployment configuration that explicitly allows
TLS 1.2 and TLS 1.3 and proxies to the local HTTP development server. It contains
paths only; certificates and private keys are intentionally not included.

A separate reproducible local Uvicorn HTTPS verifier is available at
`scripts/verify_local_https.py`. It creates a temporary SQLite database, a
throwaway Fernet key, and a self-signed certificate with `localhost` and
`127.0.0.1` Subject Alternative Names. The certificate is explicitly trusted
only by the test client, which also performs hostname/IP validation. The server
listens on loopback, enforces TLS 1.2 as its minimum, and its temporary data and
key material are removed on exit.

### Recorded local reproduction

The verifier completed successfully in the actual repository checkout on
2026-11-14 at 14:20:02 UTC:

| Check | Observed result |
|---|---:|
| TLS 1.2 | Negotiated `TLSv1.2` |
| TLS 1.3 | Negotiated `TLSv1.3` |
| TLS 1.0 | No handshake; `UNEXPECTED_EOF_WHILE_READING` |
| TLS 1.1 | No handshake; `UNEXPECTED_EOF_WHILE_READING` |
| `GET /health` | 200 |
| `GET /docs` | 200 |
| Unauthenticated `GET /accounts` | 401 |
| Teller account opening | 201 |
| Teller deposit | 201 |
| Teller withdrawal | 201 |
| Customer own-account listing | 200 |
| Customer transfer | 201 |

Environment: Python 3.12.16, OpenSSL 3.6.2, macOS 26.3 arm64. The tested
source revision was
`c93d0d0659ce913a5e497dd468a202cfcf79b175`, obtained with `git rev-parse HEAD`
before this follow-up commit.

For TLS 1.0/1.1, Uvicorn/OpenSSL closed the attempted legacy connections and the
client reported `UNEXPECTED_EOF_WHILE_READING`. This records that no legacy
handshake was established in this run; it is not an assertion that a particular
TLS alert code was returned.

### Scope and limitations

- These checks verify **local Uvicorn HTTPS**, not a deployed Nginx reverse proxy.
- The Nginx configuration was inspected; it was not deployed or tested against
a public endpoint or public-CA certificate.
- Browser output-encoding verification for the Customer UI is recorded in the
  follow-up section below. The Admin audit-log UI is not part of this main-based
  revision and remains covered separately by its unmerged PR.

## Follow-up verification (2026-11-15)

This follow-up was performed from a separate worktree based on `origin/main`
at `4e046c635aece0000d924cf328ea05f144375988`, using a disposable SQLite
database and loopback-only application ports. The live US-30 application,
monitor and CSV were not used.

### Browser output encoding

Environment: Google Chrome 157.0.8103.51, Playwright via Node 22. The browser
context used the `America/Los_Angeles` timezone. The exact command was:

```bash
NODE_PATH=/Users/vaby/.npm/_npx/e41f203b7505f1fb/node_modules \
node tests/ui/us27_xss_check.js
```

Result:

```text
PASS: hostile account/transaction values rendered as literal text; no dialog or console error
```

The test mocked disposable API responses containing HTML tags, script-like
text, an event-handler attribute, quotes and special characters. It verified
that the Customer account and transaction UI displayed the values as text and
created no HTML nodes, dialogs or browser console errors. This is genuine
browser evidence, distinct from the source-level `test_ui_safety.py` scan and
the API-level validation tests.

The Admin audit-log UI is introduced by unmerged PR #77 and is not present on
this main-based worktree. Therefore malicious audit-detail rendering in that
UI is not claimed as evidence here; it must be verified with the Admin UI
deliverable after that PR is merged or in its own isolated browser run.

### Nginx runtime verification

The exact availability checks were:

```bash
command -v nginx
docker --version
```

Neither command found an executable in this environment. No Nginx process was
started, no production port or certificate was touched, and no Nginx runtime
result is claimed. The `deploy/nginx-https.conf` protocol allow-list and proxy
headers remain source-level evidence only. The TLS 1.2/1.3 negotiation,
TLS 1.0/1.1 refusal and endpoint results recorded above are historical local
Uvicorn HTTPS evidence from 2026-11-14, not Nginx evidence.

### Regression checks

- `pytest -v`: 379 passed, 1 warning (2026-11-15 follow-up worktree).
- `pytest tests/test_security_validation.py -v`: 6 passed, 1 warning.
- `pytest tests/test_ui_safety.py -v`: 2 passed, 1 warning.
- `pytest tests/test_ui_static.py -v`: 5 passed, 1 warning.
- `python -m pip check`: No broken requirements found.
- `python -m compileall -q app scripts`: passed.
- `git diff --check`: passed.

## Reproduction commands

Run from the actual repository root using the project's Python 3.12 environment:

```bash
python -m scripts.verify_local_https
pytest -v
python -m pip check
git diff --check
git rev-parse HEAD
```

Do not commit certificates, private keys, temporary databases, Fernet keys,
access tokens, passwords, or personal identifiers. The verifier generates its
own temporary data and does not touch the regular `bms.db`.
