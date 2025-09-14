# app/tests/test_security.py
"""
Security-focused test suite for authentication, authorization, and audit logging.
"""
import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.main import app
from app.security import expected_api_key, rotate_api_key, preview_api_key
from app.audit_logger import AuditEventType, AuditLogger
from app.security_middleware import TLSEnforcementMiddleware, EnhancedSecurityHeadersMiddleware


class TestAPIKeySecurity:
    """Test API key security mechanisms."""
    
    def test_no_api_key_configured_allows_access(self):
        """In dev mode without API key, should allow access."""
        with patch.dict(os.environ, {}, clear=True):
            client = TestClient(app)
            response = client.get("/health")
            assert response.status_code == 200
    
    def test_valid_api_key_header_allows_access(self):
        """Valid API key in header should allow access."""
        test_key = "sk-test123456789"
        with patch.dict(os.environ, {"X_API_KEY": test_key}):
            client = TestClient(app)
            response = client.get("/health", headers={"x-api-key": test_key})
            assert response.status_code == 200
    
    def test_invalid_api_key_header_denies_access(self):
        """Invalid API key in header should deny access."""
        with patch.dict(os.environ, {"X_API_KEY": "sk-valid123"}):
            client = TestClient(app)
            # Try to access an endpoint that requires authentication without session
            response = client.post("/analyze/tx", json={
                "tx_id": "test", "timestamp": "2024-01-01T00:00:00", "chain": "XRPL",
                "from_addr": "test", "to_addr": "test", "amount": 100, "symbol": "XRP",
                "direction": "out", "memo": "", "fee": 0.1
            }, headers={"x-api-key": "sk-invalid456"})
            assert response.status_code == 401
            assert "unauthorized" in response.json()["detail"].lower()
    
    def test_api_key_rotation(self):
        """Test API key rotation functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock the data directory using pathlib.Path
            from pathlib import Path
            temp_path = Path(temp_dir)
            with patch("app.security._DATA_DIR", temp_path):
                with patch("app.security._KEY_FILE", temp_path / "api_key.secret"):
                    with patch("app.security._META_FILE", temp_path / "api_key.meta"):
                        # Generate initial key
                        key1 = rotate_api_key()
                        assert key1.startswith("sk-")
                        assert len(key1) > 10
                        
                        # Rotate to new key
                        key2 = rotate_api_key()
                        assert key2.startswith("sk-")
                        assert key1 != key2
                        
                        # Verify new key is active
                        assert expected_api_key() == key2
    
    def test_api_key_preview_security(self):
        """Test that API key preview doesn't expose full key."""
        test_key = "sk-test123456789abcdef"
        with patch.dict(os.environ, {"X_API_KEY": test_key}):
            preview = preview_api_key()
            assert preview["configured"] is True
            assert "test123" not in preview["preview"]
            assert preview["preview"].startswith("sk-t")
            assert preview["preview"].endswith("cdef")


class TestTLSEnforcement:
    """Test TLS enforcement middleware."""
    
    def test_tls_redirect_in_production(self):
        """HTTP requests should redirect to HTTPS in production."""
        middleware = TLSEnforcementMiddleware(app=None, enforce_tls=True)
        
        # Mock request
        request = MagicMock()
        request.url.scheme = "http"
        request.method = "GET"
        request.url.path = "/dashboard"
        request.url.replace.return_value = "https://example.com/dashboard"
        request.headers = {}
        
        # Mock call_next
        async def call_next(req):
            return None
        
        # Test redirect
        import asyncio
        response = asyncio.run(middleware.dispatch(request, call_next))
        assert response.status_code == 301
    
    def test_tls_enforcement_disabled_in_dev(self):
        """TLS enforcement should be disabled in development."""
        middleware = TLSEnforcementMiddleware(app=None, enforce_tls=False)
        
        request = MagicMock()
        request.url.scheme = "http"
        request.method = "GET"
        request.url.path = "/dashboard"
        
        # Mock successful response
        mock_response = MagicMock()
        async def call_next(req):
            return mock_response
        
        import asyncio
        response = asyncio.run(middleware.dispatch(request, call_next))
        assert response == mock_response


class TestSecurityHeaders:
    """Test security headers middleware."""
    
    def test_security_headers_applied(self):
        """Test that security headers are properly applied."""
        client = TestClient(app)
        response = client.get("/")
        
        # Test for essential security headers
        assert "Content-Security-Policy" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "Referrer-Policy" in response.headers
        
        # Verify CSP includes basic protections
        csp = response.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "object-src 'none'" in csp
        assert "frame-ancestors 'none'" in csp
    
    def test_hsts_header_on_https(self):
        """Test HSTS header is set for HTTPS requests in production."""
        middleware = EnhancedSecurityHeadersMiddleware(app=None)
        
        # Mock HTTPS request
        request = MagicMock()
        request.url.scheme = "https"
        request.headers = {}
        
        # Mock response
        response = MagicMock()
        response.headers = {}
        
        async def call_next(req):
            return response
        
        with patch.dict(os.environ, {"APP_ENV": "production"}):
            import asyncio
            result = asyncio.run(middleware.dispatch(request, call_next))
            assert "Strict-Transport-Security" in result.headers


class TestAuditLogging:
    """Test audit logging functionality."""
    
    def test_audit_logger_initialization(self):
        """Test audit logger initializes correctly."""
        logger = AuditLogger()
        assert logger.logger is not None
        assert logger.logger.name == "klerno.audit"
    
    def test_auth_success_logging(self):
        """Test authentication success logging."""
        logger = AuditLogger()
        
        with patch.object(logger.logger, 'info') as mock_log:
            logger.log_auth_success("user123", "test@example.com", "admin")
            mock_log.assert_called_once()
            
            # Verify log contains expected information
            call_args = mock_log.call_args
            assert "auth.login.success" in call_args[0][0]
            assert call_args[1]["extra"]["audit_event"]["user_id"] == "user123"
            assert call_args[1]["extra"]["audit_event"]["user_email"] == "test@example.com"
    
    def test_auth_failure_logging(self):
        """Test authentication failure logging."""
        logger = AuditLogger()
        
        with patch.object(logger.logger, 'info') as mock_log:
            logger.log_auth_failure("test@example.com", "invalid_password")
            mock_log.assert_called_once()
            
            call_args = mock_log.call_args
            assert "auth.login.failure" in call_args[0][0]
            assert call_args[1]["extra"]["audit_event"]["outcome"] == "failure"
    
    def test_security_event_logging(self):
        """Test security event logging."""
        logger = AuditLogger()
        
        with patch.object(logger.logger, 'info') as mock_log:
            logger.log_security_event(
                AuditEventType.CSRF_VIOLATION,
                {"endpoint": "/api/test", "reason": "missing_token"},
                risk_score=0.8
            )
            mock_log.assert_called_once()
            
            call_args = mock_log.call_args
            assert "security.csrf.violation" in call_args[0][0]
            assert call_args[1]["extra"]["audit_event"]["risk_score"] == 0.8


class TestCSRFProtection:
    """Test CSRF protection mechanisms."""
    
    def test_csrf_cookie_issued(self):
        """Test that CSRF token cookie is issued."""
        client = TestClient(app)
        response = client.get("/login")
        
        # Check that CSRF cookie is set
        cookies = {name: value for name, value in response.cookies.items()}
        assert "csrf_token" in cookies
        assert len(cookies["csrf_token"]) > 20  # Should be a substantial token
    
    def test_csrf_protection_on_post(self):
        """Test CSRF protection on POST requests."""
        client = TestClient(app)
        
        # Try POST without CSRF token
        response = client.post("/uiapi/analyze/sample")
        # Should be redirected to login or return 403/401
        assert response.status_code in [401, 403, 302, 307]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])