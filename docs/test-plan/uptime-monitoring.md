# BMS uptime monitoring

The uptime monitor polls the BMS health endpoint and appends one observation per
check to a CSV file. It records timestamps in UTC, HTTP status, response time,
success/failure status and a concise error for failed requests. Response bodies
and credentials are never written to the log.

## Defaults

- URL: `http://127.0.0.1:8000/health`
- Interval: 30 seconds
- Timeout: 5 seconds
- CSV: `docs/test-plan/uptime-log.csv`

Run the monitor from the repository root after starting the application:

```bash
python -m scripts.uptime_check
```

Stop it with `Ctrl+C`. For a controlled single observation, use:

```bash
python -m scripts.uptime_check --once
```

Options:

```text
--url URL              Health endpoint URL
--interval SECONDS     Seconds between checks
--timeout SECONDS      HTTP request timeout
--output PATH          CSV output path
--once                 Perform one check and exit
```

## CSV format

The monitor creates parent directories and writes the header only for a new
file. Subsequent observations are appended. Columns are:

`timestamp_utc,status,http_status,response_time_ms,error`

`status` is `SUCCESS` for any 2xx response and `FAILURE` for non-2xx responses,
timeouts or connection errors. Failed requests without an HTTP response leave
`http_status` empty.

Availability is calculated over a defined observation period as:

```text
Availability (%) = Successful checks / Total checks × 100
```

The CSV must contain genuine observations for the stated period. A one-shot
smoke test does not establish long-term or two-hour availability.

## Read-only availability analysis

`scripts/analyze_uptime.py` reads an explicit CSV without modifying it. It
interprets requested calendar dates in Asia/Kolkata, parses UTC/offset
timestamps, reports successful and failed observations, recorded-check
availability, HTTP status distribution, response-time statistics, slow checks,
malformed rows, irregular/missing intervals and observation coverage. It does
not silently discard failed checks and applies no maintenance exclusion; the
report states that maintenance exclusion is unverified.
Response-time values must be finite and non-negative. Invalid timing values
are counted separately and excluded from response-time statistics, while their
valid timestamp/status observations remain in availability totals.

Example for the complete November 2026 IST calendar month (run after the month
has ended):

```bash
python -m scripts.analyze_uptime \
  --input /path/to/read-only-uptime-log.csv \
  --start-date 2026-11-01 --end-date 2026-12-01
```

The current date is before November 30, 2026, so no complete-month November
availability result is claimed and issue #23 remains open. The tracked live
CSV is never modified by the analyzer; take only a read-only temporary
snapshot after the observation period is complete.
