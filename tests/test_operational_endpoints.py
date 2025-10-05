import pytest
from fastapi.testclient import TestClient

# Import the FastAPI app
from app.main import app

client = TestClient(app)


def test_ready_endpoint() -> None:
    resp = client.get("/ready")
    assert resp.status_code in (200, 503)
    data = resp.json()
    assert "status" in data
    assert "uptime_seconds" in data


def test_metrics_endpoint_optional() -> None:
    resp = client.get("/metrics")
    # If prometheus_client not installed, endpoint might 404 (skip) else 200
    if resp.status_code == 404:
        pytest.skip("metrics disabled / dependency not installed")
    assert resp.status_code == 200
    assert b"http_requests_total" in resp.content


def test_security_headers_present() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    # Minimal set of security headers we add
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert "max-age" in resp.headers.get("Strict-Transport-Security", "")
