# Integrated transaction load test (BMS-NF-001, TC-Perf-01)

Target: at least 95% of deposit, withdrawal and transfer requests complete within 3 seconds with 50 users.

## Tested source and environment

Application source commit: `e86d5d7d396d3d77e2b80a0cae0007ca0690d725`. This local integration includes PR #63 head `f8a234b46a2bb2877ec8530bc4f0d58bcdc72bdc` and PR #64 head `808c835ba6ab15d8d3f8e49e58b69d3f8ea503d9`. Merge these PRs before #65. Later evidence-only commits do not change the application or workload.

Run date: 15 November 2026 (local time). Windows 11 build 26200, Intel64 Family 6 Model 183 Stepping 1, 32 logical CPUs; Python 3.12.14 and Locust 2.47.0. See [exact dependencies](load-test-requirements.txt) and [configuration manifest](load-test-manifest.json).

- 50 users: 25 Tellers and 25 Customers; spawn rate 10 users/second.
- Duration: 120 seconds, including ramp-up and login. Login latency is excluded from transaction statistics.
- All 50 users authenticated successfully; no login failures.
- Fresh isolated SQLite database, verified WAL, 30,000 ms busy timeout, pool 5 + 10.
- Single API process and local HTTP; Rs 1 per transaction. Transaction notification creation is enabled.

## Results

| Endpoint | Requests | Failures | Median (ms) | p95 (ms) |
|---|---:|---:|---:|---:|
| /transactions/deposit | 1,888 | 0 | 310 | 480 |
| /transactions/transfer | 3,190 | 0 | 310 | 480 |
| /transactions/withdraw | 1,214 | 0 | 310 | 500 |
| Aggregated | 6,292 | 0 | 310 | 490 |

**Result: PASS for this measured local workload.** Every endpoint p95 was below 3,000 ms, with zero transaction failures and zero pool timeout tracebacks. This is a short local observation, not a production performance guarantee. Locust percentile estimates are rounded histogram values, not maximum response times.

The [CSV statistics](load-test_stats.csv), [user-count history](load-test_stats_history.csv), [failures](load-test_failures.csv), [exceptions](load-test_exceptions.csv) and [server log](load-test-server.log) retain the supporting evidence. CSV line endings are normalized for Git without changing nonempty records.

## Post-run integrity checks

Read-only inspection reconciled all 10 account balances with their seeded values plus the full transaction ledger. There were 9,482 transaction rows and 9,482 notification rows. Deposit, withdrawal and transfer audit counts matched the successful request counts. Transfers have separate debit and credit rows. See [ledger check results](load-test-ledger-check.json).

The seed balance is 10,000 times customer index for Savings and 20,000 + 5,000 times index for Current (indices 1-5). For each account, the check adds Deposit/TransferIn amounts and subtracts Withdrawal/TransferOut amounts. It also compares request counts to transaction types, notification count to total transaction rows, and successful audit counts to requests.

## Reproduce

Use an environment with `requirements.txt` and `locust==2.47.0`, then run from the committed repository root:

```powershell
python tests/load/run_pool_experiment.py --output "$env:TEMP\bms-integrated-load-new-run" --configurations R3 --repeats 1
```

Choose a new output directory. The runner uses an isolated database and throwaway key, verifies settings, records login counts and stops its own server. Its normal default still runs the 12 comparison runs documented for PR #63.

## Limits

One two-minute local run includes ramp-up and authentication startup; the full window is not steady-state traffic from 50 fully authenticated users. The server and generator share a normal-use workstation. This does not measure deployed HTTPS/network overhead, production capacity, longer workloads or monthly availability. Final release integration changes require fresh validation. The earlier 7 November results have been replaced because they did not test this combined application.
