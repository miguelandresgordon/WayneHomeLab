"""Health endpoint and SQLite ping."""


def test_health_ok(client) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"
    assert body["version"] == "0.1.0-test"


def test_health_has_no_pii_keys(client) -> None:
    body = client.get("/api/v1/health").json()
    assert "email" not in body
    assert "token" not in body
    assert set(body) == {"status", "db", "version"}
