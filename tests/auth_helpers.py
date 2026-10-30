"""Helpers for tests that need a logged-in user. Owner: Ronit.

Usage in a test:
    from tests.auth_helpers import act_as
    act_as("Teller")                      # the next requests behave as a logged-in Teller
    act_as("Customer", customer_id=5)     # a Customer who owns customer 5
The `client` fixture in conftest.py clears the override after each test.
"""
from types import SimpleNamespace

from app.deps import get_current_user
from app.main import app


def act_as(role: str, customer_id: int | None = None, user_id: int = 1, must_change_password: bool = False):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=user_id,
        username=f"test-{role.lower()}",
        role=role,
        customer_id=customer_id,
        must_change_password=must_change_password,
    )
