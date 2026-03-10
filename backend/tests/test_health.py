"""Smoke tests for the health endpoint."""


def test_health_returns_ok(client):
    """GET /api/v1/health should return 200 with status ok."""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
