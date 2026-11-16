# Final integrated transaction load test (BMS-NF-001, TC-Perf-01)

Target: at least 95% of deposit, withdrawal and transfer requests complete within 3 seconds with 50 users.

## Tested source and environment

Application/workload source commit: `2a29889703e839f015c3152e7844f7d1509026f7`. This integrates main `f5eff882878c6f6a5cc546910bdbb8c3e22ab5cd`, including merged PRs #60 and #61. The application tree `8d106e1f7c4a5336c557254689d8a23ad6b1419c` exactly matches that main revision. Subsequent evidence-only commits do not change the measured application or workload.

Execution began 2026-11-16T17:45:25.119509+05:30 (IST), 16 November 2026. Windows 11 build 26200, Intel64 Family 6 Model 183 Stepping 1, 32 logical CPUs; Python 3.12.14 and Locust 2.47.0. See [dependency versions](load-test-requirements.txt) and [configuration manifest](load-test-manifest.json).

- 50 users: 25 Tellers and 25 Customers; spawn rate 10 users/second. History reaches 50 users.
- Duration: 120 seconds including ramp-up and login; process elapsed 121.57 seconds including shutdown. Login latency is excluded from transaction statistics.
- All 50 users authenticated successfully; no login failures.
- Fresh isolated SQLite database; verified WAL, 30,000 ms busy timeout and pool 5 + 10.
- Single API process and local HTTP; Rs 1 per transaction. Transaction notifications and append-only audit triggers are enabled.

## Results

| Endpoint | Requests | Failures | Median (ms) | p95 (ms) |
|---|---:|---:|---:|---:|
| /transactions/deposit | 2,577 | 0 | 22 | 61 |
| /transactions/transfer | 4,313 | 0 | 24 | 61 |
| /transactions/withdraw | 1,679 | 0 | 24 | 62 |
| Aggregated | 8,569 | 0 | 23 | 61 |

**PASS for this measured local workload.** Every endpoint p95 is below 3,000 ms, with zero transaction failures and zero pool timeout tracebacks. Percentiles are Locust histogram estimates, not maximum response times.

The [final CSV statistics](load-test_stats.csv) are captured at Locust's quit event after all users stop, including requests completed during shutdown. Its normal periodic CSV may precede the final requests; that [periodic snapshot](load-test_periodic-stats.csv) is retained separately and is not used for ledger reconciliation. A preliminary run exposed this periodic-snapshot mismatch; the reporting harness was corrected and the complete 120-second run was repeated. The final evidence here comes from that fresh repeated run.

Supporting evidence includes [user-count history](load-test_stats_history.csv), [failures](load-test_failures.csv), [exceptions](load-test_exceptions.csv), [Locust output](load-test-locust.log), [server output](load-test-server.log), and artifact SHA-256 hashes in the manifest. CSV line endings are normalized without changing nonempty records.

## Post-run integrity checks

Read-only checks reconciled all 10 account balances and every intermediate transaction balance. There are 12,882 transaction rows and 12,882 matching notification records. All 4,313 transfer references have exactly one debit and one matching credit for different accounts. Notification message/customer counts match the ledger, and successful audit counts match final request counts. SQLite integrity and foreign-key checks pass, and both append-only audit triggers are installed.

Initial total balance: Rs 325000; final total balance: Rs 325898. The net change equals deposits minus withdrawals; transfers conserve total money. [Full reconciliation results](load-test-ledger-check.json).

## Verification

- Full pytest suite on the integrated application: **448 passed, 1 warning** (227.75 seconds). The warning is the existing Starlette/httpx deprecation. Reporting-only harness changes were subsequently verified by the complete benchmark and reconciliation above.
- `python -m pip check`: no broken requirements found.
- Working project database untouched; its original SHA-256 remains unchanged.
- Final PR-head CI is checked separately after the evidence commit is pushed.

## Reproduce

Use Python 3.12 with `requirements.txt` and `locust==2.47.0`. Run from the committed repository root, selecting a new external output directory:

```powershell
python tests/load/run_pool_experiment.py --output "$env:TEMP\bms-final-load-new-run" --configurations R3 --repeats 1
python tests/load/check_load_ledger.py --run "$env:TEMP\bms-final-load-new-run\R3-1"
```

The runner archives the exact source commit, creates an isolated database and throwaway key, verifies its settings, captures final statistics and stops its own loopback server. Its default invocation still supports the 12 comparison runs documented for PR #63.

## Limits

This is one two-minute local HTTP run including ramp-up and authentication startup, not 120 seconds of steady-state traffic from 50 authenticated users. The server and generator share a normal-use workstation. It does not establish deployed HTTPS/network performance, sustained production capacity or monthly availability. The three transaction endpoints are measured; UI browser timing and other endpoints are outside this benchmark. Later application changes require fresh validation. Part of issue #15.
