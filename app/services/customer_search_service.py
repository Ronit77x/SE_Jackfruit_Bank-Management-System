"""Customer search service logic (US-13, BMS-F-014, TC-Acc-05). Owner: Member 2 (Vijay)."""

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.errors import AppError
from app.models import Account, Customer

ALLOWED_PHONE_CHARS = set("0123456789 -+().")


def mask_account_number(number: str | None) -> str:
    """Mask account number showing only the last 4 digits (BMS-SR-007).

    - Only accepts exactly 10 numeric digits as a valid account number (BR-06).
    - For valid 10-digit numbers: returns '******' followed by the last four digits.
    - For every malformed non-empty value (fewer or more than 10 digits, letters, spaces,
      special characters): returns '**********' (10 asterisks) without revealing any characters.
    - For None, empty strings, or whitespace-only strings: returns ''.
    """
    if number is None:
        return ""
    clean = str(number).strip()
    if not clean:
        return ""
    if len(clean) == 10 and clean.isdigit():
        return "******" + clean[-4:]
    return "**********"


def extract_phone_core(query: str) -> str | None:
    """Extract standard 10-digit core phone number if query is a valid phone representation.

    Rejects queries containing letters or other non-phone characters.
    Rejects queries that have fewer than 10 digits to prevent partial phone matching.
    Handles country code (+91 / 91) and leading zero (0) prefixes.
    """
    clean = query.strip()
    if not clean or not set(clean).issubset(ALLOWED_PHONE_CHARS):
        return None

    digits = "".join(ch for ch in clean if ch.isdigit())
    if len(digits) == 10:
        return digits
    if len(digits) == 11 and digits.startswith("0"):
        return digits[1:]
    if len(digits) == 12 and digits.startswith("91"):
        return digits[2:]
    return None


def get_relevant_accounts(customer: Customer, query: str) -> list[Account]:
    """Return relevant accounts for a customer based on search type (Task 5).

    - If search matches a specific account number, return only that matching account.
    - If search is by customer name or phone, return all associated accounts.
    """
    clean_q = query.strip()
    matching_accounts = [acc for acc in customer.accounts if acc.account_number == clean_q]
    if matching_accounts:
        return matching_accounts
    return list(customer.accounts)


def search_customers(db: Session, query: str) -> list[Customer]:
    """Search customers by name, phone number, or account number (BMS-F-014).

    - Name matching: case-insensitive partial match with escaped wildcards.
    - Phone matching: normalized exact match; rejects partial phone matching.
    - Account matching: exact match on account number using SQL EXISTS subquery.
    - No-results response: returns generic 404 without echoing raw search query.
    """
    clean_q = (query or "").strip()
    if not clean_q:
        raise AppError(
            status_code=400,
            code="INVALID_SEARCH_QUERY",
            message="Search query cannot be empty or whitespace only.",
        )

    if len(clean_q) > 100:
        raise AppError(
            status_code=400,
            code="INVALID_SEARCH_QUERY",
            message="Search query is too long (maximum 100 characters).",
        )

    # 1. Name search: case-insensitive partial match
    escaped_name = clean_q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    conditions = [Customer.name.ilike(f"%{escaped_name}%", escape="\\")]

    # 2. Phone search: exact normalized phone matching
    phone_core = extract_phone_core(clean_q)
    if phone_core:
        # Strip common formatting characters from stored phone column in SQL (including periods)
        clean_phone_col = func.replace(
            func.replace(
                func.replace(
                    func.replace(
                        func.replace(
                            func.replace(Customer.phone, "-", ""),
                            " ", "",
                        ),
                        "+", "",
                    ),
                    "(", "",
                ),
                ")", "",
            ),
            ".", "",
        )
        conditions.append(
            and_(
                func.length(clean_phone_col) >= 10,
                func.substr(clean_phone_col, -10) == phone_core,
            )
        )
    # Also support direct raw equality on phone
    conditions.append(Customer.phone == clean_q)

    # 3. Account search: exact match via EXISTS subquery
    conditions.append(Customer.accounts.any(Account.account_number == clean_q))

    stmt = (
        select(Customer)
        .where(or_(*conditions))
        .options(selectinload(Customer.accounts))
        .order_by(Customer.id.asc())
    )

    customers = list(db.scalars(stmt).all())
    if not customers:
        raise AppError(
            status_code=404,
            code="CUSTOMER_NOT_FOUND",
            message="No customers found matching the supplied search criteria.",
        )

    return customers
