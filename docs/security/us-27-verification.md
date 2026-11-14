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
- Browser output-encoding verification remains pending because this repository
  has no browser-rendered UI in the verified scope.

### Regression checks

- `pytest -v`: 160 passed, 1 warning.
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
