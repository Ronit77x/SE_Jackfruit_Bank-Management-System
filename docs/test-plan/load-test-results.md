# Load test results (BMS-NF-001, TC-Perf-01)

**Requirement:** 95 % of deposit, withdrawal and transfer requests complete within 3 seconds with 50 concurrent users.


| Item | Value |
|---|---|
| Date and time of the run | 07-11-2026 14:17:51 |
| Machine (CPU, RAM, operating system) | HP OMEN Gaming Laptop 16-wf0xxx; 13th Gen Intel Core i9-13900HX; 14,710,988,800 bytes RAM (13.7 GiB); Microsoft Windows 11 |
| Commit tested (`git rev-parse --short HEAD`) | 3eabcc9 |
| Command | `locust -f tests/load/locustfile.py --headless -u 50 -r 10 -t 2m --host http://127.0.0.1:8000 --csv docs/test-plan/load-test` |
| Users / ramp-up / duration | 50 / 10 per second / 2 minutes |
| Database | SQLite (WAL mode) |

## Results (from `docs/test-plan/load-test_stats.csv`)

| Endpoint | Requests | Failures | Median (ms) | 95th percentile (ms) |
|---|---|---|---|---|
| /transactions/deposit | 2598 | 0 | 21 | 63 |
| /transactions/withdraw | 1657 | 0 | 23 | 67 |
| /transactions/transfer | 4292 | 0 | 23 | 66 |
| **Aggregated** | 8547 | 0 | 23 | 65 |

**Verdict: PASS — BMS-NF-001 satisfied.**

The aggregated 95th-percentile response time was 65 ms, below the required 3000 ms threshold. All 8547 measured requests completed without reported failures.

## Notes

- Login requests were excluded from the measured statistics because BMS-NF-001 specifically evaluates deposit, withdrawal and transfer performance.
- The test used SQLite in WAL mode with the API server and Locust running locally.
- All 8,547 measured requests completed with zero reported failures.
- The aggregate median response time was 23 ms, and the 95th-percentile response time was 65 ms.
- The maximum observed response time was approximately 659 ms.
- The test met the requirement of completing at least 95% of requests within 3,000 ms.
- No application errors were reported by Locust during the measured run.
- The results reflect a local test environment and may differ under production network conditions or sustained workloads.

## Limitations

- The test was performed locally, with the API server and load generator running on the same machine.
- Authentication requests were excluded from performance measurements.
- All transactions used a fixed amount of Rs. 1.
- Results may vary under production network conditions and longer workloads.