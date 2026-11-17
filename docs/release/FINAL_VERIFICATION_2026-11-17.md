# Final submission verification ? 17 November 2026

## Verified baseline and agreement

- Application and documentation checkout tested: `754d03c6d86927e490438ff7286c76f8258a2a12` (main after PR #84).
- Team agreement on the submission baseline and documented limitations: confirmed by Ronit on 17 November 2026.
- Application scope freeze: 17 November 2026 at that commit. This follow-up changes documentation only; its eventual merge commit is the submission's documentation revision, not a different application implementation.
- [Main GitHub Actions ? Run Pytest Suite: passed](https://github.com/SEMiniProjectBMS/SE_Jackfruit_Bank-Management-System/actions/runs/44110370545).
- No Git tag or GitHub Release creation is claimed.

## Independent final regression

An isolated checkout was tested on Windows with Python 3.12.14 using the existing verification virtual environment and disposable SQLite databases and test directories. The user's working checkout and database were not used. This was not a fresh dependency installation.

Command (temporary paths represented by placeholders):

```text
BMS_DATABASE_URL=sqlite:///<disposable-database>
python -B -m pytest -q -p no:cacheprovider --basetemp <disposable-test-directory> --tb=short
```

**Result: 447 passed, 1 skipped, 1 warning in 120.87 seconds.**

The skip is `tests/test_teller_accounts_ui.py:119`: the Playwright module was not installed in this environment. This run therefore does not establish that optional browser check passed. A focused diagnostic rerun reported 12 passed, 1 skipped, 1 warning and confirmed that reason. The warning is the existing Starlette/httpx TestClient deprecation warning. Earlier 409/448 counts are historical evidence, not this final local result.

`python -m pip check`: **No broken requirements found.**

## Setup and smoke verification

- Generated an ephemeral Fernet key in the process environment and ran `python -B -m scripts.seed` against a separate fresh SQLite database: **Seed data loaded**.
- Started the application lifespan through FastAPI TestClient: `/`, `/ui/`, `/ui/index.html`, `/docs` and `/health` returned HTTP 200 (redirects followed).
- `/health` returned `{"status":"ok"}`. This checks process responsiveness, not database readiness.
- These are in-process smoke checks, not a new visual-browser, Uvicorn-network or deployed-HTTPS verification run.
- Relative links in the final README, release documents, deviations and demo record were checked for existing targets.
- Both demo files exist. Sprint 1: 4,824,067 bytes; Sprint 2: 13,322,370 bytes.
- Sprint 2 SHA-256: `06ba4731df487dca24202f3aa1f3a42196c26df70b1061bd651b7345efc67966`, matching the supplied recording copied without re-encoding.

## Acceptance limitations and closure

The [complete deviations log](../deviations.md) remains authoritative. In particular, five-user usability acceptance, complete latest-two-browser-version/physical-touchscreen coverage and monthly availability are not established. Issues #12, #13 and #23 were verified closed as **Not planned** for remaining evaluation. Team agreement does not change these criteria, fabricate results or claim an assessor waiver. The Sprint 2 video exceeds the assignment's two-minute target.

PR #84 finalizes US-07 documentation. After this final verification-record PR is reviewed and merged, and its main CI passes, issue #36 can be closed as **Completed**. Review of this documentation update and its post-merge CI remain normal publication checks, rather than unrecorded application verification.
