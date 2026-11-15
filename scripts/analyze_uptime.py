"""Read-only analysis of genuine uptime-monitor CSV observations."""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path


IST = timezone(timedelta(hours=5, minutes=30), "IST")
UTC = timezone.utc
CSV_FIELDS = {"timestamp_utc", "status", "http_status", "response_time_ms", "error"}


def _period(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    if end_date <= start_date:
        raise ValueError("end date must be after start date")
    return (
        datetime.combine(start_date, time.min, tzinfo=IST).astimezone(UTC),
        datetime.combine(end_date, time.min, tzinfo=IST).astimezone(UTC),
    )


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def analyze(path: Path, start_date: date, end_date: date, interval_seconds: float = 30.0) -> dict[str, object]:
    """Analyze rows without modifying *path*; end_date is exclusive in IST."""
    period_start, period_end = _period(start_date, end_date)
    rows_read = 0
    malformed_rows = 0
    outside_period = 0
    observations: list[tuple[datetime, dict[str, str]]] = []
    with path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        if not reader.fieldnames or not CSV_FIELDS.issubset(reader.fieldnames):
            raise ValueError("CSV is missing required uptime columns")
        for row in reader:
            rows_read += 1
            try:
                timestamp = _parse_timestamp(row.get("timestamp_utc", ""))
                if row.get("status") not in {"SUCCESS", "FAILURE"}:
                    raise ValueError("unknown status")
            except (TypeError, ValueError):
                malformed_rows += 1
                continue
            if not period_start <= timestamp < period_end:
                outside_period += 1
                continue
            observations.append((timestamp, row))

    observations.sort(key=lambda item: item[0])
    total = len(observations)
    successes = sum(row["status"] == "SUCCESS" for _, row in observations)
    failures = total - successes
    availability = (successes / total * 100) if total else None
    http_statuses = Counter(row.get("http_status") or "<none>" for _, row in observations)
    response_times = []
    for _, row in observations:
        try:
            response_times.append(float(row["response_time_ms"]))
        except (TypeError, ValueError):
            malformed_rows += 1
    intervals = [
        (current - previous).total_seconds()
        for (previous, _), (current, _) in zip(observations, observations[1:])
    ]
    irregular = [gap for gap in intervals if gap <= 0 or gap > interval_seconds * 1.5]
    missing = sum(max(0, math.ceil(gap / interval_seconds) - 1) for gap in irregular if gap > 0)
    period_seconds = (period_end - period_start).total_seconds()
    observed_span = (observations[-1][0] - observations[0][0]).total_seconds() if total > 1 else 0.0
    return {
        "input": str(path),
        "period": {
            "start_ist": datetime.combine(start_date, time.min, tzinfo=IST).isoformat(),
            "end_ist_exclusive": datetime.combine(end_date, time.min, tzinfo=IST).isoformat(),
            "start_utc": period_start.isoformat(),
            "end_utc_exclusive": period_end.isoformat(),
        },
        "rows_read": rows_read,
        "observations": total,
        "successful_observations": successes,
        "failed_observations": failures,
        "recorded_availability_percent": round(availability, 6) if availability is not None else None,
        "target_percent": 99.5,
        "target_met_by_recorded_checks": availability is not None and availability >= 99.5,
        "http_status_distribution": dict(sorted(http_statuses.items())),
        "response_time_ms": {
            "count": len(response_times),
            "min": min(response_times) if response_times else None,
            "max": max(response_times) if response_times else None,
            "average": round(sum(response_times) / len(response_times), 6) if response_times else None,
            "at_least_1000ms": sum(value >= 1000 for value in response_times),
        },
        "malformed_rows": malformed_rows,
        "outside_requested_period": outside_period,
        "coverage": {
            "first_observation_utc": observations[0][0].isoformat() if observations else None,
            "last_observation_utc": observations[-1][0].isoformat() if observations else None,
            "observed_span_seconds": observed_span,
            "requested_period_seconds": period_seconds,
            "span_coverage_percent": round(observed_span / period_seconds * 100, 6) if period_seconds else 0,
            "irregular_intervals": len(irregular),
            "estimated_missing_intervals": missing,
            "expected_interval_seconds": interval_seconds,
        },
        "maintenance_adjustment": "none applied; scheduled maintenance exclusions remain unverified",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze uptime observations without modifying the CSV")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--start-date", type=date.fromisoformat, required=True, help="IST date, inclusive")
    parser.add_argument("--end-date", type=date.fromisoformat, required=True, help="IST date, exclusive")
    parser.add_argument("--interval-seconds", type=float, default=30.0)
    args = parser.parse_args()
    print(json.dumps(analyze(args.input, args.start_date, args.end_date, args.interval_seconds), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
