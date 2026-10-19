"""Shared constants. Values come from the SRS business rules (BR-01..BR-08).

Do not change these without telling the team: the SRS, SAD and Test Plan use the same numbers.
Owner: Member 3 (Ronit).
"""
from decimal import Decimal

# Roles (BMS-F-003)
ROLE_CUSTOMER = "Customer"
ROLE_TELLER = "Teller"
ROLE_ADMIN = "Admin"

# User status (BMS-F-002, BMS-F-030)
USER_ACTIVE = "Active"
USER_LOCKED = "Locked"
USER_INACTIVE = "Inactive"

# Account types and status (BMS-F-010, BMS-F-012)
ACCOUNT_SAVINGS = "Savings"
ACCOUNT_CURRENT = "Current"
ACCOUNT_ACTIVE = "Active"
ACCOUNT_FROZEN = "Frozen"
ACCOUNT_CLOSED = "Closed"

# Transaction types (BMS-F-020..F-022)
TXN_OPENING_DEPOSIT = "OpeningDeposit"
TXN_DEPOSIT = "Deposit"
TXN_WITHDRAWAL = "Withdrawal"
TXN_TRANSFER_OUT = "TransferOut"
TXN_TRANSFER_IN = "TransferIn"

# Business rules
MIN_BALANCE = {ACCOUNT_SAVINGS: Decimal("1000"), ACCOUNT_CURRENT: Decimal("5000")}  # BR-01
DAILY_WITHDRAWAL_LIMIT = Decimal("50000")  # BR-02
TRANSFER_LIMIT = Decimal("100000")  # BR-03
DEPOSIT_LIMIT = Decimal("200000")  # BR-03
MAX_FAILED_LOGINS = 3  # BR-07
SESSION_IDLE_MINUTES = 10  # BMS-SR-003
