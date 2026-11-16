"""In-memory login sessions (token -> session data). Lost when the server restarts.

Kept in its own module so that both app/deps.py and app/routers/auth.py can import it without importing each other.
"""

_sessions: dict[str, dict] = {}
