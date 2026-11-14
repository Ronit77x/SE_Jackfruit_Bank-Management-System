# SQLite connection-pool experiment

PR #63 keeps SQLite's default pool (5 + 10), enables WAL and a 30-second busy timeout, and applies connection-health options only to client/server databases.

## Configurations and workload

| Label | Journal | Busy timeout | Pool size + overflow |
|---|---|---|---|
| R0 original | DELETE | 5 seconds | 5 + 10 |
| R1 | WAL | 30 seconds | 40 + 10 |
| R2 | WAL | 30 seconds | 50 + 50 |
| R3 current defaults | WAL | 30 seconds | 5 + 10 |

Each configuration runs three times for **120 seconds (2 minutes)**, with 50 users, a spawn rate of 10 users/second, and a freshly seeded database for every run. Half the users are Tellers depositing/withdrawing; half are Customers transferring. Amounts are Rs 1. The two-minute window includes ramp-up and login; login latency is excluded from transaction statistics, and successful/failed login counts are recorded separately. This is a single-process local HTTP workload. It does not verify deployed HTTPS performance or monthly availability.

Runs alternate R0, R1, R2, R3 in each of three rounds. R0 uses the original database module from the recorded baseline commit; every other application file is identical to the benchmark source commit. R1-R3 use the updated module with environment overrides. Before starting each server, the runner checks the actual journal, timeout and pool settings. Fresh files prevent WAL state leaking into R0.

## Reproduce safely

Use a separate Python environment containing `requirements.txt` and `locust==2.47.0`. Commit the source first. From the repository root:

```powershell
python tests/load/run_pool_experiment.py --output "$env:TEMP\bms-pool-experiment-new-run"
```

Choose an output directory that does not exist. The runner snapshots committed source, creates isolated databases and throwaway encryption keys, starts its own server on port 8770, and stops that server after each run. It does not reset the repository's database or overwrite working source. Use `--port` if 8770 is occupied. The baseline defaults to main commit `380edd9037f3d1b61a018978c552a56739664b22`; use `--baseline <SHA>` to select another original baseline. The exact baseline SHA and module hashes are recorded in `results.json`.

The underlying Locust invocation is identical to the harness instructions:

```powershell
locust -f tests/load/locustfile.py --headless -u 50 -r 10 -t 120s --host http://127.0.0.1:8770 --csv <run-directory>/load --csv-full-history --stop-timeout 10
```

Keep `results.json`, dependency versions, per-run CSVs and logs. Review startup login counts and errors as well as the aggregate latency. A run is invalid if any of the 50 users fails login. Transaction failures remain part of the evidence, even when Locust exits with code 1.

## Your machine

Collected on 14-15 November 2026 (local time), Windows 11 build 26200, Intel64 Family 6 Model 183 Stepping 1, 32 logical CPUs; Python 3.12.14, Locust 2.47.0. Exact installed versions are in [requirements-freeze.txt](test-plan/pool-experiment/requirements-freeze.txt).

**Benchmark source commit:** `474371310d21e44e185321f05553c53a6187f02d`. **R0 baseline module commit:** `380edd9037f3d1b61a018978c552a56739664b22`. R1-R3 used the updated configuration from the benchmark source commit. Subsequent evidence and instruction-comment changes do not alter application code or workload behavior. The journal, timeout and pool were checked on each fresh database before starting its server.

Updated database module SHA-256: `6ae35883d8bb204c0e007783485db70acd5a0b73bf4e9b26d147f96dae45115f`. Baseline module SHA-256: `45eaa0ca341d0814ed69932d82ea0cf0643df86a4fb56c2ab2dd821bc7f66fc7`.

| Run | Requests | Failures | Median (ms) | p95 (ms) | Pool timeouts | Successful logins |
|---|---:|---:|---:|---:|---:|---:|
| R0-1 | 5,159 | 0 | 190 | 1300 | 0 | 50/50 |
| R1-1 | 7,477 | 0 | 30 | 310 | 0 | 50/50 |
| R2-1 | 8,599 | 0 | 23 | 59 | 0 | 50/50 |
| R3-1 | 8,567 | 0 | 23 | 62 | 0 | 50/50 |
| R0-2 | 4,325 | 0 | 320 | 2100 | 0 | 50/50 |
| R1-2 | 7,059 | 0 | 38 | 330 | 0 | 50/50 |
| R2-2 | 7,574 | 0 | 34 | 360 | 0 | 50/50 |
| R3-2 | 5,920 | 0 | 250 | 370 | 0 | 50/50 |
| R0-3 | 3,497 | 0 | 620 | 2100 | 0 | 50/50 |
| R1-3 | 6,867 | 0 | 46 | 360 | 0 | 50/50 |
| R2-3 | 5,817 | 0 | 280 | 390 | 0 | 50/50 |
| R3-3 | 5,829 | 0 | 270 | 390 | 0 | 50/50 |

| Configuration | Request-count range | Aggregate p95 range (ms) | Median of run p95s (ms) |
|---|---:|---:|---:|
| R0 | 3,497-5,159 | 1300-2100 | 2100 |
| R1 | 6,867-7,477 | 310-360 | 330 |
| R2 | 5,817-8,599 | 59-390 | 360 |
| R3 | 5,829-8,567 | 62-390 | 370 |

**Observed result:** all twelve runs had zero transaction failures, zero pool timeout tracebacks, and 50 successful logins. The original configuration did not reproduce the earlier reported HTTP 500 errors. WAL plus the longer timeout delivered lower aggregate p95 latency in all three rounds. Increasing the WAL pool did not provide a consistent advantage over the default pool, so the default 5 + 10 remains appropriate for this measured workload. This comparison changes WAL and busy timeout together; it does not isolate their individual contributions.

All 36 per-endpoint p95 measurements were below 3,000 ms. These are Locust histogram estimates, not maximum response times; some individual requests exceeded three seconds. The load generator and server ran on the same normal-use workstation. No claim of statistical significance or production capacity follows from three short runs.

**Reviewable evidence:** [results and configuration manifest](test-plan/pool-experiment/results.json), [per-endpoint summary](test-plan/pool-experiment/endpoint-summary.csv), [server logs](test-plan/pool-experiment/server-logs.txt), and the twelve `*_stats.csv` / `*_stats_history.csv` pairs in [pool-experiment](test-plan/pool-experiment/). History CSVs record the ramp to 50 users. Original complete output, disposable databases and unabridged Locust logs remain in the external benchmark folder; no encryption keys or tokens are included in committed evidence.

Earlier Claude sandbox numbers were removed because their raw evidence is unavailable. The measurements above replace them.

## Interpretation and limits

WAL permits a reader and writer to coexist, but SQLite still has one writer at a time. The focused tests verify this behavior and backend-specific engine options. The load experiment compares the configurations; it must not assume that R0 will fail or that larger pools will help. These short local runs cannot establish production capacity. Compare failures, request counts and variation between repeats before drawing conclusions.
