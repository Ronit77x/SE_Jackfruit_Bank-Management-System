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

Actual results are being collected against the committed updated configuration. The final evidence will identify the source commit, machine, dependency versions and all twelve runs. Earlier Claude sandbox numbers have been removed because their raw evidence is unavailable; they are not machine measurements for this PR.

## Interpretation and limits

WAL permits a reader and writer to coexist, but SQLite still has one writer at a time. The focused tests verify this behavior and backend-specific engine options. The load experiment compares the configurations; it must not assume that R0 will fail or that larger pools will help. These short local runs cannot establish production capacity. Compare failures, request counts and variation between repeats before drawing conclusions.

