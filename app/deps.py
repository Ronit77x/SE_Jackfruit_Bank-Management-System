"""Shared FastAPI dependencies. Owner: Member 1 (Tarini), stories US-01 and US-03.

!!! TEMPORARY STUB !!!
Until Tarini's login (US-01) and role checks (US-03) are merged, `get_current_user` returns a fake
user whose role comes from the optional request header `X-Test-Role` (default: Admin). This lets
everyone build and test their endpoints now. Tarini replaces the body of these two functions with
the real implementation and KEEPS THE FUNCTION NAMES AND SIGNATURES, so nobody else has to change code.

Usage in a router:
    from app.deps import require_roles
    @router.post("/accounts")
    def open_account(user = Depends(require_roles("Teller")), db = Depends(get_db)): ...
"""
from types import SimpleNamespace

from fastapi import Depends, Header

from app.constants import ROLE_ADMIN


def get_current_user(x_test_role: str | None = Header(default=None)):
    return SimpleNamespace(id=0, username="stub-user", role=x_test_role or ROLE_ADMIN, customer_id=None)


def require_roles(*allowed_roles: str):
    """Returns a dependency that allows only the given roles (real version: HTTP 403 otherwise)."""

    def checker(user=Depends(get_current_user)):
        return user

    return checker
