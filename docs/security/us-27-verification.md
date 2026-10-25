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

Verified locally: configuration inspection confirms `ssl_protocols TLSv1.2
TLSv1.3` and no certificate/key material is tracked. A live TLS handshake was
not performed because no deployed endpoint or test certificates are available.
Browser output-encoding verification remains pending because this repository has
no browser-rendered UI.

## Commands

Run from the repository root:

```text
pytest tests/test_security_validation.py
pytest
git diff --check
```
