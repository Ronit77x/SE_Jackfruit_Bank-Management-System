"""Transaction endpoints. Owner: Member 3 (Ronit). Stories: US-17, US-18, US-19, US-20, US-21.

Planned endpoints (SAD section 4.3):
  POST /transactions/deposit    {accountId, amount}                  (Teller)
  POST /transactions/withdraw   {accountId, amount}                  (Teller)
  POST /transactions/transfer   {fromAccount, toAccount, amount}     (Customer)
  GET  /accounts/{id}/transactions?from=&to=                         (Customer)
  GET  /accounts/{id}/statement?format=csv|pdf                       (Customer)
"""
from fastapi import APIRouter

router = APIRouter(tags=["transactions"])
