"""
Test health endpoints for Klerno Labs application.

This module tests the /health and /healthz endpoints to ensure they return
proper responses and status codes.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client for the application."""
    from app.main import app
    return TestClient(app)


def test_health_endpoint(client):
    """Test that /health endpoint returns 200 OK with proper response."""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    # Basic health check should return status and timestamp
    assert "status" in data
    assert data["status"] == "ok"
    assert "timestamp" in data


def test_healthz_endpoint(client):
    """Test that /healthz endpoint returns 200 OK (Kubernetes-style health check)."""
    response = client.get("/healthz")
    
    assert response.status_code == 200
    
    # Healthz endpoint may return simple text or JSON
    if response.headers.get("content-type", "").startswith("application/json"):
        data = response.json()
        assert "status" in data
    else:
        # Simple text response
        assert "ok" in response.text.lower() or response.text.strip() == "200"


def test_health_endpoint_headers(client):
    """Test that health endpoint includes proper headers."""
    response = client.get("/health")
    
    assert response.status_code == 200
    
    # Should include security headers from SecurityHeadersMiddleware
    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    
    assert "X-Frame-Options" in response.headers
    assert response.headers["X-Frame-Options"] == "DENY"


def test_health_endpoint_no_auth_required(client):
    """Test that health endpoints don't require authentication."""
    # Health endpoints should be accessible without any auth headers or keys
    response = client.get("/health")
    assert response.status_code == 200
    
    response = client.get("/healthz")
    assert response.status_code == 200


@pytest.mark.integration
def test_health_endpoint_performance(client):
    """Test that health endpoint responds quickly."""
    import time
    
    start_time = time.time()
    response = client.get("/health")
    end_time = time.time()
    
    assert response.status_code == 200
    
    # Health check should respond in under 1 second
    assert (end_time - start_time) < 1.0