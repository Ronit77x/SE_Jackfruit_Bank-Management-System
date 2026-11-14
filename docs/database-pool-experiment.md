# SQLite settings under 50 simultaneous users: what was measured

## Why this was looked at
The first 50-user load test (`tests/load/locustfile.py`) produced a few HTTP 500 errors. The server log showed
`sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached, connection timed out`.

## What was tried
Four configurations, same workload each time, only the database settings differ:

| Label | Journal mode | Pool (size + overflow) | How it is set |
|---|---|---|---|
| R0 original | default (rollback journal), SQLite default timeout | 5 + 10 | the original `app/database.py` |
| R1 | WAL, 30 s busy timeout | 40 + 10 | `BMS_DB_POOL_SIZE=40 BMS_DB_MAX_OVERFLOW=10` |
| R2 | WAL, 30 s busy timeout | 50 + 50 | `BMS_DB_POOL_SIZE=50 BMS_DB_MAX_OVERFLOW=50` |
| R3 (current) | WAL, 30 s busy timeout | 5 + 10 | defaults |

**Workload (identical for all):** `tests/load/locustfile.py`, 50 users (half Tellers doing deposits and withdrawals,
half Customers doing transfers), ramp-up 10 users per second, 60 seconds, freshly seeded database, amounts of Rs 1.
The login is not measured. Statistics are the aggregate of the three money endpoints.

## Results (one run each, sandbox with a single CPU core)

| Run | Requests | Failures | Median (ms) | 95th percentile (ms) | `QueuePool` tracebacks in the server log |
|---|---|---|---|---|---|
| R0 original | 1,256 | 5 | 13 | 55 | 20 |
| R1 pool 40 + 10, WAL | 3,800 | 0 | 10 | 26 | 0 |
| R2 pool 50 + 50, WAL | 3,644 | 0 | 11 | 32 | 0 |
| R3 pool 5 + 10, WAL | 3,668 | 0 | 8 | 22 | 0 |

An earlier run of R0 gave 1,205 requests and 10 failures; an earlier run of R1 gave 3,650 requests, 0 failures and a 95th percentile of 32 ms.

## What this shows
- **WAL (plus the 30 s busy timeout) is what removed the errors.** Without it, readers and the single writer block each
  other, requests wait while holding their connections, and after 30 seconds the pool gives up (R0). With WAL the
  small default pool is enough (R3).
- **The pool size makes no measurable difference.** R1, R2 and R3 are within normal run-to-run variation of each other.
  This is expected: SQLite allows one writer at a time whatever the pool size, so more connections cannot add write
  throughput; they only add memory and file handles. The pool was therefore **returned to SQLAlchemy's default
  (5 + 10)**. An earlier change to 50 + 50 was based on the wrong explanation and is withdrawn.
- A test (`tests/test_database_config.py`) proves the mechanism: in the default journal mode a writer cannot commit
  while a reader is open; in WAL mode it can.
- `pool_pre_ping` and `pool_recycle` are only set for client/server databases (for example PostgreSQL), where idle
  connections can be closed by the server or a firewall. They are not needed for a local SQLite file.

## Limits of this evidence
Single 60-second runs on a one-core sandbox. The absolute numbers depend on the machine. Repeat the runs (three each)
on your own machine and fill in the table below; the conclusion to check is whether R0 fails and R1-R3 do not.

## How to repeat it
In one terminal (virtual environment active, repository root):
```powershell
python -m scripts.seed
uvicorn app.main:app
```
In a second terminal:
```powershell
locust -f tests/load/locustfile.py --headless -u 50 -r 10 -t 60s --host http://127.0.0.1:8000 --csv docs/test-plan/pool-run
```
Read the `Aggregated` row of `docs/test-plan/pool-run_stats.csv` (Request Count, Failure Count, 50%, 95%).
For each configuration stop the server, delete `bms.db*`, run `python -m scripts.seed`, set the variables, and start again:
```powershell
$env:BMS_DB_POOL_SIZE = "40"; $env:BMS_DB_MAX_OVERFLOW = "10"     # R1; use 50/50 for R2; remove both variables for R3
Remove-Item Env:BMS_DB_POOL_SIZE, Env:BMS_DB_MAX_OVERFLOW        # back to the defaults
```
To reproduce R0, restore the original file from an earlier commit and put the current one back afterwards:
```powershell
git log --oneline -- app/database.py                  # pick the commit before this fix
git show <that-commit>:app/database.py > app/database.py
git checkout -- app/database.py                       # restore the current version
```

## Your machine (fill in from your own runs)

| Run | Requests | Failures | Median (ms) | 95th percentile (ms) |
|---|---|---|---|---|
| R0 original | | | | |
| R1 pool 40 + 10, WAL | | | | |
| R2 pool 50 + 50, WAL | | | | |
| R3 pool 5 + 10, WAL | | | | |
