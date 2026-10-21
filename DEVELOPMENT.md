# Development guide

## Run it

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1          # if PowerShell blocks this, run: Set-ExecutionPolicy -Scope Process Bypass
pip install -r requirements.txt
uvicorn app.main:app --reload        # then open http://127.0.0.1:8000/docs
pytest                               # run all tests
```
Always run commands from the repository root (the folder that contains `app/` and `tests/`).

## Who edits which files (this avoids merge conflicts)

| Member | Files you own |
|---|---|
| Member 1 (Tarini) | `app/routers/auth.py`, `app/deps.py`, `app/security.py`, `.github/workflows/`, `tests/test_auth*.py` |
| Member 2 (Vijay) | `app/routers/accounts.py`, `app/services/account_service.py`, `tests/conftest.py`, `tests/test_accounts*.py` |
| Member 3 (Ronit) | `app/main.py`, `app/database.py`, `app/models.py`, `app/constants.py`, `app/routers/transactions.py`, `app/services/transaction_service.py`, `tests/test_models.py`, `tests/test_transactions*.py` |
| Member 4 (Vaibhav) | `app/routers/admin.py`, `app/services/audit_service.py`, `tests/test_admin*.py`, `tests/test_audit*.py` |

Create new files freely inside your own area (for example `app/services/account_service.py`). If you need to change a file owned by someone else, ask the owner in the group chat or make a small additive change in your own PR and say so in the PR description.

## Shared building blocks (already in place)

- `app.database.get_db` — database session dependency.
- `app.deps.require_roles("Teller")` — role check (temporary stub until US-01/US-03 are merged; the function name never changes).
- `app.services.audit_service.log_event(db, user_id, action, outcome, details)` — write an audit record. Never pass passwords or full account numbers.
- `app.security.hash_password / verify_password` — bcrypt helpers.
- `app.constants` — roles, statuses and the business-rule numbers (BR-01..BR-08). Use these instead of typing numbers.

## Branches and pull requests

1. `git checkout main` then `git pull`
2. `git checkout -b feature/US-xx-short-name`
3. Work, then commit often: `git commit -m "feat(US-xx): what you did"`
4. `git push -u origin feature/US-xx-short-name`
5. On GitHub open a PR into `main`, title `[US-xx] Title`, description `Closes #<issue number>`, request your reviewer.
6. The repo owner merges with "Create a merge commit".
Never commit directly to `main`. Never force-push.

## Running tests

Activate the virtual environment before running tests.
Run `pytest` from the repository root to execute all tests.
Run `pytest tests/test_accounts.py -v` to run account tests only.
