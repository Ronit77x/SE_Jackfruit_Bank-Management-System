import csv
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

from scripts.analyze_uptime import analyze


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = ["timestamp_utc", "status", "http_status", "response_time_ms", "error"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def row(timestamp, status="SUCCESS", http_status="200", response="10", error=""):
    return {"timestamp_utc": timestamp, "status": status, "http_status": http_status, "response_time_ms": response, "error": error}


def test_analysis_uses_ist_boundaries_and_preserves_failures(tmp_path):
    source = tmp_path / "uptime.csv"
    write_csv(source, [
        row("2026-10-31T18:29:59Z"),
        row("2026-10-31T18:30:00Z"),  # 2026-11-01 00:00 IST
        row("2026-11-01T00:00:30Z", "FAILURE", "", "1001", "timeout"),
        row("2026-12-01T00:00:00Z"),
    ])
    result = analyze(source, date(2026, 11, 1), date(2026, 11, 2))
    assert result["observations"] == 2
    assert result["successful_observations"] == 1
    assert result["failed_observations"] == 1
    assert result["recorded_availability_percent"] == 50.0
    assert result["http_status_distribution"] == {"<none>": 1, "200": 1}
    assert result["response_time_ms"]["at_least_1000ms"] == 1


def test_analysis_reports_malformed_rows_gaps_and_never_writes_source(tmp_path):
    source = tmp_path / "uptime.csv"
    write_csv(source, [row("2026-11-01T00:00:00Z"), row("bad"), row("2026-11-01T00:02:00Z", response="1200")])
    before = source.read_bytes()
    result = analyze(source, date(2026, 11, 1), date(2026, 11, 2))
    assert result["malformed_rows"] == 1
    assert result["coverage"]["irregular_intervals"] == 1
    assert result["coverage"]["estimated_missing_intervals"] == 3
    assert result["response_time_ms"]["at_least_1000ms"] == 1
    assert source.read_bytes() == before


def test_cli_emits_json(tmp_path):
    source = tmp_path / "uptime.csv"
    write_csv(source, [row("2026-11-01T00:00:00Z")])
    output = subprocess.check_output([
        sys.executable, "-m", "scripts.analyze_uptime", "--input", str(source),
        "--start-date", "2026-11-01", "--end-date", "2026-12-01",
    ], text=True)
    assert json.loads(output)["observations"] == 1
