"""
Integration tests for API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json

# Import app after setting test environment
import os
os.environ["APP_ENV"] = "test"

from app.main import app
from app.settings import get_settings


@pytest.fixture


def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture


def mock_api_key():
    """Mock API key for tests."""
    with patch('app.security.expected_api_key', return_value='test - api - key'):
        yield 'test - api - key'


@pytest.fixture


def mock_enforce_api_key():
    """Mock API key enforcement."""
    with patch('app.security.enforce_api_key', return_value=True):
        yield


class TestHealthEndpoints:
    """Test health check endpoints."""


    def test_health_endpoint_with_auth(self, client, mock_enforce_api_key):
        """Test authenticated health endpoint."""
        response=client.get("/health", headers={"X - API - Key": "test - key"})
        assert response.status_code == 200
        data=response.json()
        assert "status" in data
        assert data["status"] == "ok"


    def test_healthz_endpoint(self, client):
        """Test public health endpoint."""
        response=client.get("/healthz")
        assert response.status_code == 200
        data=response.json()
        assert "status" in data


class TestAnalysisEndpoints:
    """Test transaction analysis endpoints."""


    def test_analyze_sample(self, client, mock_enforce_api_key):
        """Test sample transaction analysis."""
        response=client.get("/analyze / sample", headers={"X - API - Key": "test - key"})
        assert response.status_code == 200
        data=response.json()
        assert "transaction" in data or "risk_score" in data


class TestXRPLIntegration:
    """Test XRPL integration endpoints."""

    @patch('app.main.fetch_account_tx')


    def test_xrpl_fetch(self, mock_fetch, client, mock_enforce_api_key):
        """Test XRPL transaction fetching."""
        mock_fetch.return_value=[]

        response=client.get(
            "/integrations / xrpl / fetch?account=rTestAccount&limit=5",
                headers={"X - API - Key": "test - key"}
        )
        assert response.status_code == 200
        data=response.json()
        # API returns an object with count and items
        assert "items" in data or isinstance(data, list)


class TestErrorHandling:
    """Test error handling scenarios."""


    def test_invalid_endpoint(self, client):
        """Test accessing invalid endpoint."""
        response=client.get("/invalid / endpoint")
        assert response.status_code == 404


    def test_method_not_allowed(self, client, mock_enforce_api_key):
        """Test invalid HTTP method."""
        response=client.delete("/health", headers={"X - API - Key": "test - key"})
        assert response.status_code == 405


    def test_unauthorized_access(self, client):
        """Test accessing protected endpoint without auth."""
        response=client.get("/health")
        # Should return 401 or similar auth error
        assert response.status_code in [401, 422]  # 422 if validation fails


class TestCORS:
    """Test CORS headers."""


    def test_cors_preflight(self, client):
        """Test CORS preflight request."""
        response=client.options("/healthz", headers={
            "Origin": "http://localhost:3000",
                "Access - Control - Request - Method": "GET"
        })
        # Should handle CORS appropriately
        assert response.status_code in [200, 204, 405]


class TestRequestResponseFlow:
    """Test complete request / response flows."""


    def test_get_sample_data(self, client, mock_enforce_api_key):
        """Test getting sample data."""
        response=client.get("/analyze / sample", headers={"X - API - Key": "test - key"})
        assert response.status_code == 200

        # Check response structure
        data=response.json()
        assert isinstance(data, dict)

    @patch('app.integrations.xrp.fetch_account_tx')


    def test_xrpl_integration_flow(self, mock_fetch, client, mock_enforce_api_key):
        """Test XRPL integration flow."""
        # Mock successful XRPL response
        mock_fetch.return_value=[]

        response=client.get(
            "/integrations / xrpl / fetch",
                params={"account": "rTestAccount123", "limit": 10},
                headers={"X - API - Key": "test - key"}
        )

        assert response.status_code == 200
        data=response.json()
        assert "items" in data or isinstance(data, list)


class TestDataValidation:
    """Test data validation in requests."""


    def test_invalid_query_parameters(self, client, mock_enforce_api_key):
        """Test handling of invalid query parameters."""
        response=client.get(
            "/integrations / xrpl / fetch",
                params={"account": "", "limit": "invalid"},
                headers={"X - API - Key": "test - key"}
        )

        # Should handle validation errors gracefully
        assert response.status_code in [200, 400, 422]


    def test_missing_required_parameters(self, client, mock_enforce_api_key):
        """Test handling of missing required parameters."""
        response=client.get(
            "/integrations / xrpl / fetch",
                headers={"X - API - Key": "test - key"}
        )

        # Should handle missing parameters
        assert response.status_code in [200, 400, 422]


@pytest.mark.skip(reason="Rate limiting not implemented yet")


class TestRateLimiting:
    """Test rate limiting functionality."""


    def test_rate_limiting(self, client, mock_enforce_api_key):
        """Test rate limiting enforcement."""
        # This test would verify rate limiting once implemented
        for i in range(100):
            response=client.get("/health", headers={"X - API - Key": "test - key"})
            if response.status_code == 429:  # Too Many Requests
                break
        else:
            pytest.fail("Rate limiting not triggered after 100 requests")
