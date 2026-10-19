"""Authentication endpoints. Owner: Member 1 (Tarini). Stories: US-01, US-02, US-03, US-04, US-05.

Planned endpoints (SAD section 4.3):
  POST /auth/login      body {username, password} -> {token, role, mustChangePassword}; 401 / 423
  POST /auth/logout
  PUT  /auth/password   body {currentPassword, newPassword}; 400 weak, 401 wrong current
"""
from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])
