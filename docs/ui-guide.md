# Building a browser page

All pages live in `app/static/` and are served by the application at `/ui/` (for example `app/static/customer.html` is `http://127.0.0.1:8000/ui/customer.html`). Start from `app/static/_page-template.html`.

## What you get from `js/api.js` (global object `bms`)

| Call | Purpose |
|---|---|
| `bms.requireRole(["Customer"])` | At the top of the page: sends the visitor to the login page unless a user with that role is logged in (and to the change-password page while a temporary password is still active). |
| `bms.header("Title")` | Fills `<header id="site-header">` with the page links for the logged-in role and a log-out link. |
| `await bms.get(path)`, `bms.post(path, body)`, `bms.put`, `bms.patch` | Calls the API with the login token. On failure they throw an `Error` whose `.message` is the server's readable message (`.status`, `.code` also set). A `401` sends the user back to the login page. |
| `await bms.download(path, "name.csv")` | Downloads a file with the token (a plain link cannot send it), for example the statement. |
| `bms.show(el, text, ok)` / `bms.hide(el)` | Shows or clears a message in an element with class `message`. |
| `bms.el(tag, text, className)`, `bms.clear(node)` | Build page content safely. |
| `bms.money(value)` | Formats an amount as `Rs 1,500.00`. |

## Rules

1. **Never put server text into the page as HTML.** Use `textContent` or `bms.el(...)`. The browser's HTML-insertion APIs are forbidden in every file under `app/static`; `tests/test_ui_safety.py` fails if one appears (BMS-SR-005, cross-site scripting).
2. Load only `/ui/js/api.js` and `/ui/css/style.css`; no scripts from other sites.
3. Accounts are identified by the 10-digit account number.
4. Every page needs `<meta name="viewport" ...>` and must be usable at 360 px width (use the classes in `css/style.css`: `card`, `row two`, `message`, `table-wrap`, `muted`).
5. Show amounts with `bms.money(...)`; show the masked account numbers the server returns.
6. A page for a role calls `bms.requireRole([...])` first. The server enforces the role again on every request, the page check is only for convenience.

## Trying a page

```powershell
python -m scripts.seed
uvicorn app.main:app --reload
```
Open `http://127.0.0.1:8000/`. Seeded users (password `Passw0rd!`): Customers `1`–`5`, Tellers `teller1`–`teller3`, Admin `admin1`.
