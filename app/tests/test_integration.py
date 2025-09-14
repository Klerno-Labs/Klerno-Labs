"""
Comprehensive end-to-end tests that validate the entire application setup.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import os

# Set test environment before importing the app
os.environ["APP_ENV"] = "test"

from app.main import app
from app.logging_config import configure_logging, get_logger
from app.exceptions import (
    KlernoException, 
    ValidationException, 
    AuthenticationException,
    install_exception_handlers
)
from app.middleware import (
    RequestLoggingMiddleware,
    MetricsMiddleware, 
    SecurityHeadersMiddleware,
    RateLimitMiddleware
)
from app.settings import get_settings


@pytest.fixture
def client():
    """Create test client with all middleware enabled."""
    return TestClient(app)


@pytest.fixture
def settings():
    """Get test settings."""
    # Clear the cache to ensure we get fresh settings
    get_settings.cache_clear()
    return get_settings()


class TestApplicationSetup:
    """Test overall application configuration and setup."""
    
    def test_settings_configuration(self, settings):
        """Test that settings are properly configured."""
        assert settings.app_env == "test"
        assert isinstance(settings.debug, bool)
        assert isinstance(settings.port, int)
        assert settings.port > 0
        
        # Security settings should have defaults
        assert settings.jwt_secret
        assert settings.api_key
        
        # CORS origins should be a list
        assert isinstance(settings.cors_origins, list)
    
    def test_logging_configuration(self):
        """Test that logging is properly configured."""
        # Reconfigure logging for test
        configure_logging()
        
        # Get a logger and test it works
        logger = get_logger("test")
        assert logger is not None
        
        # Test logging methods exist
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "debug")
    
    def test_exception_handling_setup(self):
        """Test that custom exceptions work properly."""
        # Test base exception
        exc = KlernoException("Test message", "TEST_CODE", 400)
        assert exc.message == "Test message"
        assert exc.error_code == "TEST_CODE"
        assert exc.status_code == 400
        
        # Test specific exceptions
        auth_exc = AuthenticationException()
        assert auth_exc.status_code == 401
        assert auth_exc.error_code == "AUTHENTICATION_ERROR"
        
        validation_exc = ValidationException("Invalid field", "field_name")
        assert validation_exc.status_code == 422
        assert validation_exc.field == "field_name"


class TestMiddlewareIntegration:
    """Test middleware functionality."""
    
    def test_security_headers_middleware(self, client):
        """Test that security headers are added."""
        response = client.get("/healthz")
        
        # Check for security headers
        expected_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options", 
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy"
        ]
        
        for header in expected_headers:
            assert header in response.headers, f"Missing security header: {header}"
    
    def test_request_id_generation(self, client):
        """Test that request IDs are generated and returned."""
        response = client.get("/healthz")
        assert "X-Request-ID" in response.headers
        
        request_id = response.headers["X-Request-ID"]
        assert len(request_id) > 0
        
        # Request ID should be different for each request
        response2 = client.get("/healthz") 
        request_id2 = response2.headers["X-Request-ID"]
        assert request_id != request_id2


class TestAPIEndpointsIntegration:
    """Test API endpoints with full middleware stack."""
    
    def test_health_endpoint_comprehensive(self, client):
        """Test health endpoint with all middleware."""
        response = client.get("/healthz")
        
        # Should succeed
        assert response.status_code == 200
        
        # Should have security headers
        assert "X-Content-Type-Options" in response.headers
        
        # Should have request ID
        assert "X-Request-ID" in response.headers
        
        # Should return proper JSON
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"
    
    @patch('app.security.enforce_api_key', return_value=True)
    def test_protected_endpoint_flow(self, mock_auth, client):
        """Test complete flow for protected endpoints."""
        response = client.get("/health", headers={"X-API-Key": "test-key"})
        
        # Should succeed with mocked auth
        assert response.status_code == 200
        
        # Should have all expected headers
        assert "X-Request-ID" in response.headers
        assert "X-Content-Type-Options" in response.headers
        
        # Response should be JSON
        data = response.json()
        assert isinstance(data, dict)
    
    def test_error_handling_integration(self, client):
        """Test that errors are handled properly with middleware."""
        # Test 404
        response = client.get("/nonexistent")
        assert response.status_code == 404
        
        # Should still have security headers
        assert "X-Content-Type-Options" in response.headers
        
        # Should have request ID
        assert "X-Request-ID" in response.headers


class TestComplianceAndSecurity:
    """Test compliance and security features."""
    
    def test_cors_configuration(self, client):
        """Test CORS is properly configured."""
        response = client.get("/healthz", headers={
            "Origin": "http://localhost:3000"
        })
        
        # Should succeed
        assert response.status_code == 200
        
        # In a real implementation, we'd check for CORS headers
        # This is a basic test to ensure the endpoint works with Origin header
    
    def test_content_type_security(self, client):
        """Test content type security measures."""
        response = client.get("/healthz")
        
        # Should have nosniff header
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        
        # Response should be proper JSON
        assert response.headers.get("content-type").startswith("application/json")
    
    def test_frame_protection(self, client):
        """Test frame protection headers."""
        response = client.get("/healthz")
        
        # Should deny framing
        assert response.headers.get("X-Frame-Options") == "DENY"
    
    def test_https_enforcement(self, client):
        """Test HTTPS enforcement headers."""
        response = client.get("/healthz")
        
        # Should have HSTS header
        hsts = response.headers.get("Strict-Transport-Security")
        assert hsts
        assert "max-age" in hsts
        assert "includeSubDomains" in hsts


class TestPerformanceAndMonitoring:
    """Test performance and monitoring features."""
    
    def test_metrics_endpoint_exists(self, client):
        """Test that metrics endpoint is available."""
        # Import metrics endpoint function
        from app.middleware import metrics_endpoint
        
        # Function should exist and be callable
        assert callable(metrics_endpoint)
        
        # Test the endpoint returns proper content
        response = metrics_endpoint()
        assert response.media_type == "text/plain; version=0.0.4; charset=utf-8"
    
    def test_response_time_tracking(self, client):
        """Test that response times are reasonable."""
        import time
        
        start_time = time.time()
        response = client.get("/healthz")
        duration = time.time() - start_time
        
        # Health check should be fast (under 1 second)
        assert duration < 1.0
        assert response.status_code == 200
    
    def test_concurrent_requests(self, client):
        """Test that the application handles concurrent requests."""
        import concurrent.futures
        import time
        
        def make_request():
            return client.get("/healthz")
        
        # Make 5 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            start_time = time.time()
            futures = [executor.submit(make_request) for _ in range(5)]
            responses = [future.result() for future in futures]
            duration = time.time() - start_time
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
        
        # Should complete within reasonable time
        assert duration < 5.0
        
        # All should have unique request IDs
        request_ids = [r.headers["X-Request-ID"] for r in responses]
        assert len(set(request_ids)) == 5  # All unique


class TestDataValidationIntegration:
    """Test data validation across the application."""
    
    def test_settings_validation(self):
        """Test that settings validation works."""
        from app.settings import Settings
        
        # Test with valid settings
        settings = Settings(app_env="test", port=8000)
        assert settings.app_env == "test"
        assert settings.port == 8000
        
        # Test defaults
        default_settings = Settings()
        assert default_settings.app_env == "dev"
        assert default_settings.port == 8000
    
    def test_json_response_validation(self, client):
        """Test that JSON responses are properly formatted."""
        response = client.get("/healthz")
        
        # Should be valid JSON
        data = response.json()
        assert isinstance(data, dict)
        
        # Should have expected structure
        assert "status" in data
        assert isinstance(data["status"], str)


@pytest.mark.integration
class TestFullApplicationIntegration:
    """Integration tests that verify the complete application works together."""
    
    def test_application_startup_shutdown(self):
        """Test that application can start and stop properly."""
        # This tests the entire application lifecycle
        test_client = TestClient(app)
        
        # Basic functionality should work
        response = test_client.get("/healthz")
        assert response.status_code == 200
        
        # Cleanup is handled automatically by TestClient
    
    def test_error_recovery(self, client):
        """Test that application recovers from errors."""
        # Test that after an error, normal requests still work
        
        # Make a bad request
        response1 = client.get("/nonexistent")
        assert response1.status_code == 404
        
        # Normal request should still work
        response2 = client.get("/healthz")
        assert response2.status_code == 200
        
        # Request IDs should be different
        assert response1.headers["X-Request-ID"] != response2.headers["X-Request-ID"]
    
    def test_environment_configuration(self):
        """Test that environment configuration works properly."""
        settings = get_settings()
        
        # Should be using test environment
        assert settings.app_env == "test"
        
        # Should have appropriate test defaults
        assert settings.debug in [True, False]  # Should be set to a boolean
        assert isinstance(settings.cors_origins, list)