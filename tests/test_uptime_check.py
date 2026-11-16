import csv

import httpx

from scripts.uptime_check import monitor, perform_health_check


def test_successful_health_response(monkeypatch):
    monkeypatch.setattr("httpx.get", lambda url, timeout: httpx.Response(200, request=httpx.Request("GET", url)))

    result = perform_health_check("http://test/health", timeout=1.25)

    assert result["status"] == "SUCCESS"
    assert result["http_status"] == 200
    assert result["error"] == ""


def test_non_success_http_status(monkeypatch):
    monkeypatch.setattr("httpx.get", lambda url, timeout: httpx.Response(503, request=httpx.Request("GET", url)))

    result = perform_health_check()

    assert result["status"] == "FAILURE"
    assert result["http_status"] == 503
    assert result["error"] == "HTTP status 503"


def test_connection_error(monkeypatch):
    def fail(url, timeout):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr("httpx.get", fail)

    result = perform_health_check()

    assert result["status"] == "FAILURE"
    assert result["http_status"] == ""
    assert "ConnectError" in result["error"]


def test_timeout(monkeypatch):
    def fail(url, timeout):
        raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr("httpx.get", fail)

    result = perform_health_check()

    assert result["status"] == "FAILURE"
    assert result["error"] == "timeout"


def test_csv_header_and_append(tmp_path):
    output = tmp_path / "nested" / "uptime.csv"
    observations = iter(
        [
            {"status": "SUCCESS", "http_status": 200, "response_time_ms": 1.5, "error": ""},
            {"status": "FAILURE", "http_status": 503, "response_time_ms": 2.5, "error": "HTTP status 503"},
        ]
    )

    monitor(output_path=output, once=True, check=lambda url, timeout: next(observations))
    monitor(output_path=output, once=True, check=lambda url, timeout: next(observations))

    with output.open(newline="", encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))
    assert len(rows) == 2
    assert rows[0]["status"] == "SUCCESS"
    assert rows[1]["status"] == "FAILURE"
    assert rows[1]["http_status"] == "503"


def test_configurable_url_and_timeout(tmp_path):
    received = {}

    def check(url, timeout):
        received.update(url=url, timeout=timeout)
        return {"status": "SUCCESS", "http_status": 200, "response_time_ms": 1, "error": ""}

    monitor(
        url="http://custom/health",
        timeout=2.5,
        output_path=tmp_path / "uptime.csv",
        once=True,
        check=check,
    )

    assert received == {"url": "http://custom/health", "timeout": 2.5}


def test_once_executes_one_check(tmp_path):
    calls = []

    def check(url, timeout):
        calls.append(1)
        return {"status": "SUCCESS", "http_status": 200, "response_time_ms": 1, "error": ""}

    monitor(output_path=tmp_path / "uptime.csv", once=True, check=check)

    assert len(calls) == 1


def test_keyboard_interrupt_stops_monitor_cleanly(tmp_path):
    def interrupt(_):
        raise KeyboardInterrupt

    monitor(
        output_path=tmp_path / "uptime.csv",
        sleep=interrupt,
        check=lambda url, timeout: {"status": "SUCCESS", "http_status": 200, "response_time_ms": 1, "error": ""},
    )

    assert (tmp_path / "uptime.csv").exists()
