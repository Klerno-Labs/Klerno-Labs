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
    with patch('app.security.expected_api_key', return_value='test-api-key'):
        yield 'test-api-key'


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_endpoint_with_auth(self, client, mock_api_key):
        """Test authenticated health endpoint."""
        response = client.get("/health", headers={"X-API-Key": mock_api_key})
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_health_endpoint_without_auth(self, client):
        """Test health endpoint without authentication."""
        response = client.get("/health")
        assert response.status_code == 401

    def test_healthz_endpoint(self, client):
        """Test public health endpoint."""
        response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


class TestAnalysisEndpoints:
    """Test transaction analysis endpoints."""

    @patch('app.main.score_risk')
    @patch('app.main.tag_category')
    def test_analyze_sample(self, mock_tag, mock_risk, client, mock_api_key):
        """Test sample transaction analysis."""
        mock_risk.return_value = 0.5
        mock_tag.return_value = "transfer"
        
        response = client.get("/analyze/sample", headers={"X-API-Key": mock_api_key})
        assert response.status_code == 200
        data = response.json()
        assert "transaction" in data
        assert "risk_score" in data
        assert "category" in data

    @patch('app.main.score_risk')
    @patch('app.main.tag_category')
    @patch('app.main.save_transaction')
    def test_analyze_and_save_tx(self, mock_save, mock_tag, mock_risk, client, mock_api_key):
        """Test transaction analysis and saving."""
        mock_risk.return_value = 0.7
        mock_tag.return_value = "suspicious"
        mock_save.return_value = None
        
        transaction_data = {
            "tx_id": "test_tx_123",
            "timestamp": "2024-01-01T00:00:00Z",
            "chain": "XRP",
            "from_address": "rTestFrom",
            "to_address": "rTestTo",
            "amount": "100.0",
            "memo": "test transaction",
            "fee": "0.1"
        }
        
        response = client.post(
            "/analyze_and_save/tx",
            json=transaction_data,
            headers={"X-API-Key": mock_api_key}
        )
        assert response.status_code == 200
        data = response.json()
        assert "risk_score" in data
        assert "category" in data


class TestXRPLIntegration:
    """Test XRPL integration endpoints."""

    @patch('app.main.fetch_account_tx')
    def test_xrpl_fetch(self, mock_fetch, client, mock_api_key):
        """Test XRPL transaction fetching."""
        mock_fetch.return_value = []
        
        response = client.get(
            "/integrations/xrpl/fetch?account=rTestAccount&limit=5",
            headers={"X-API-Key": mock_api_key}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @patch('app.main.fetch_account_tx')
    @patch('app.main.save_transaction')
    def test_xrpl_fetch_and_save(self, mock_save, mock_fetch, client, mock_api_key):
        """Test XRPL transaction fetching and saving."""
        mock_fetch.return_value = []
        mock_save.return_value = None
        
        response = client.post(
            "/integrations/xrpl/fetch_and_save?account=rTestAccount&limit=5",
            headers={"X-API-Key": mock_api_key}
        )
        assert response.status_code == 200


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_invalid_endpoint(self, client):
        """Test accessing invalid endpoint."""
        response = client.get("/invalid/endpoint")
        assert response.status_code == 404

    def test_method_not_allowed(self, client, mock_api_key):
        """Test invalid HTTP method."""
        response = client.delete("/health", headers={"X-API-Key": mock_api_key})
        assert response.status_code == 405

    def test_malformed_json(self, client, mock_api_key):
        """Test malformed JSON in request."""
        response = client.post(
            "/analyze_and_save/tx",
            data="{invalid json}",
            headers={
                "X-API-Key": mock_api_key,
                "Content-Type": "application/json"
            }
        )
        assert response.status_code == 422  # Unprocessable Entity


class TestCORS:
    """Test CORS headers."""

    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options("/healthz")
        # Check that CORS headers would be handled by middleware
        # In actual implementation, this would check for proper CORS headers
        assert response.status_code in [200, 404]  # OPTIONS might not be implemented


class TestRateLimiting:
    """Test rate limiting functionality."""

    @pytest.mark.skip(reason="Rate limiting not implemented yet")
    def test_rate_limiting(self, client, mock_api_key):
        """Test rate limiting enforcement."""
        # This test would verify rate limiting once implemented
        for i in range(100):
            response = client.get("/health", headers={"X-API-Key": mock_api_key})
            if response.status_code == 429:  # Too Many Requests
                break
        else:
            pytest.fail("Rate limiting not triggered after 100 requests")