"""Account and customer endpoints. Owner: Member 2 (Vijay). Stories: US-08, US-09, US-10, US-12, US-13.

Planned endpoints (baseline Part A section 3):
  POST  /accounts                 open account (+ customer login with temporary password)  (Teller)
  PUT   /customers/{id}           update contact details                                  (Teller)
  PATCH /accounts/{id}/status     freeze / unfreeze / close                               (Admin)
  GET   /accounts/{id}            details + balance (own accounts only)                   (Customer)
  GET   /customers?q=             search                                                  (Teller)
"""
from fastapi import APIRouter

router = APIRouter(tags=["accounts"])
