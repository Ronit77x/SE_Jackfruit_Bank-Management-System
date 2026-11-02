"""Poll the BMS health endpoint and append observations to a CSV log.

Run once from the repository root with::

    python -m scripts.uptime_check --once

The default long-running monitor checks ``http://127.0.0.1:8000/health`` every
30 seconds and writes ``docs/test-plan/uptime-log.csv``.
"""
import argparse
import csv
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import httpx


DEFAULT_URL = "http://127.0.0.1:8000/health"
DEFAULT_INTERVAL = 30.0
DEFAULT_TIMEOUT = 5.0
DEFAULT_OUTPUT = Path("docs/test-plan/uptime-log.csv")
CSV_FIELDS = ("timestamp_utc", "status", "http_status", "response_time_ms", "error")


def perform_health_check(url: str = DEFAULT_URL, timeout: float = DEFAULT_TIMEOUT) -> dict[str, object]:
    """Perform one health check without logging the response body."""
    started = time.perf_counter()
    try:
        response = httpx.get(url, timeout=timeout)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        if 200 <= response.status_code < 300:
            return {
                "status": "SUCCESS",
                "http_status": response.status_code,
                "response_time_ms": elapsed_ms,
                "error": "",
            }
        return {
            "status": "FAILURE",
            "http_status": response.status_code,
            "response_time_ms": elapsed_ms,
            "error": f"HTTP status {response.status_code}",
        }
    except httpx.TimeoutException:
        return {
            "status": "FAILURE",
            "http_status": "",
            "response_time_ms": round((time.perf_counter() - started) * 1000, 2),
            "error": "timeout",
        }
    except httpx.RequestError as exc:
        return {
            "status": "FAILURE",
            "http_status": "",
            "response_time_ms": round((time.perf_counter() - started) * 1000, 2),
            "error": f"{type(exc).__name__}: {exc}",
        }


def write_observation(output_path: Path, observation: dict[str, object]) -> None:
    """Append one timestamped observation, creating the directory and header as needed."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    needs_header = not output_path.exists() or output_path.stat().st_size == 0
    row = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        **observation,
    }
    with output_path.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        if needs_header:
            writer.writeheader()
        writer.writerow(row)


def monitor(
    url: str = DEFAULT_URL,
    interval: float = DEFAULT_INTERVAL,
    timeout: float = DEFAULT_TIMEOUT,
    output_path: Path = DEFAULT_OUTPUT,
    once: bool = False,
    sleep: Callable[[float], None] = time.sleep,
    check: Callable[[str, float], dict[str, object]] = perform_health_check,
) -> None:
    """Run health checks until ``once`` or Ctrl+C stops the monitor."""
    if interval < 0:
        raise ValueError("interval must not be negative")
    if timeout <= 0:
        raise ValueError("timeout must be positive")

    try:
        while True:
            write_observation(output_path, check(url, timeout))
            if once:
                return
            sleep(interval)
    except KeyboardInterrupt:
        return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitor BMS health availability.")
    parser.add_argument("--url", default=DEFAULT_URL, help="Health endpoint URL")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL, help="Seconds between checks")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="HTTP timeout in seconds")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output CSV path")
    parser.add_argument("--once", action="store_true", help="Perform one check and exit")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    monitor(args.url, args.interval, args.timeout, args.output, args.once)


if __name__ == "__main__":
    main()
