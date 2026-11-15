import time


def test_health_returns_ok(client):
    started = time.perf_counter()
    response = client.get("/health")
    elapsed = time.perf_counter() - started

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert elapsed < 1
