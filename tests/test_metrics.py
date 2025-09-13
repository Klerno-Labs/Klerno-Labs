"""
Test metrics endpoints and contract for Klerno Labs application.

This module tests the metrics API endpoints to ensure they return
proper data structures and maintain API contracts.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client for the application."""
    from app.main import app
    return TestClient(app)


def test_metrics_ui_endpoint_structure(client):
    """Test that /metrics-ui returns expected data structure."""
    # Note: This endpoint may require authentication in production
    # For now, test the basic structure when accessible
    
    response = client.get("/metrics-ui")
    
    # May return 401/403 if auth is required, which is acceptable
    if response.status_code in [401, 403]:
        pytest.skip("Metrics endpoint requires authentication")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify expected metrics structure
    assert isinstance(data, dict)
    
    # Should contain basic metrics fields
    expected_fields = ["total", "alerts", "avg_risk"]
    for field in expected_fields:
        assert field in data, f"Missing expected field: {field}"
    
    # Validate data types
    assert isinstance(data["total"], (int, float))
    assert isinstance(data["alerts"], (int, float)) 
    assert isinstance(data["avg_risk"], (int, float))


def test_metrics_ui_with_days_parameter(client):
    """Test that /metrics-ui accepts days parameter."""
    response = client.get("/metrics-ui?days=7")
    
    # May require auth
    if response.status_code in [401, 403]:
        pytest.skip("Metrics endpoint requires authentication")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should include series data for chart
    if "series_by_day" in data:
        assert isinstance(data["series_by_day"], list)


def test_metrics_ui_categories_structure(client):
    """Test that metrics include categories data."""
    response = client.get("/metrics-ui?days=30")
    
    if response.status_code in [401, 403]:
        pytest.skip("Metrics endpoint requires authentication")
    
    assert response.status_code == 200
    data = response.json()
    
    # Categories should be a dict mapping category names to counts
    if "categories" in data:
        assert isinstance(data["categories"], dict)
        
        # Each category should have a numeric count
        for category, count in data["categories"].items():
            assert isinstance(category, str)
            assert isinstance(count, (int, float))
            assert count >= 0


def test_recent_data_endpoint_structure(client):
    """Test that /uiapi/recent returns expected structure."""
    response = client.get("/uiapi/recent?limit=10")
    
    if response.status_code in [401, 403]:
        pytest.skip("Recent data endpoint requires authentication")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return items array
    assert "items" in data
    assert isinstance(data["items"], list)
    
    # Each item should have required transaction fields
    if data["items"]:
        item = data["items"][0]
        expected_fields = ["timestamp", "from_addr", "to_addr", "amount"]
        
        for field in expected_fields:
            assert field in item, f"Missing field {field} in transaction item"


@pytest.mark.api
def test_export_csv_endpoint_accessibility(client):
    """Test that CSV export endpoint is accessible."""
    response = client.get("/uiapi/export/csv/download")
    
    # Should either return CSV data or require authentication
    assert response.status_code in [200, 401, 403]
    
    if response.status_code == 200:
        # Should be CSV content
        assert "text/csv" in response.headers.get("content-type", "").lower() or \
               "application/csv" in response.headers.get("content-type", "").lower()


@pytest.mark.integration
def test_metrics_cache_behavior(client):
    """Test that metrics caching works properly."""
    # Make multiple requests to test caching
    response1 = client.get("/metrics-ui")
    
    if response1.status_code in [401, 403]:
        pytest.skip("Metrics endpoint requires authentication")
    
    response2 = client.get("/metrics-ui")
    
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    # Responses should be consistent (cached)
    data1 = response1.json()
    data2 = response2.json()
    
    # Basic metrics should be the same (allowing for minor timing differences)
    assert data1["total"] == data2["total"]
    assert data1["alerts"] == data2["alerts"]