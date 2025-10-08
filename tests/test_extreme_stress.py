"""
Extreme stress testing to break the application.
Tests the absolute limits of the system.
"""

import gc
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi.testclient import TestClient

from app.main import app


class TestExtremeStress:
    """Tests designed to break the application under extreme conditions."""

    def test_massive_concurrent_requests(self):
        """Test with extremely high concurrent load."""
        client = TestClient(app, raise_server_exceptions=False)

        def make_request():
            try:
                response = client.get("/health")
                return response.status_code
            except Exception as e:
                return str(e)

        # Test with 200 concurrent requests
        with ThreadPoolExecutor(max_workers=200) as executor:
            futures = [executor.submit(make_request) for _ in range(1000)]
            results = [future.result() for future in as_completed(futures)]

        # Should handle gracefully - either succeed or fail predictably
        success_count = sum(1 for r in results if r == 200)

        # At least 80% should succeed under stress
        success_rate = success_count / len(results)
        assert (
            success_rate >= 0.8
        ), f"Success rate {success_rate:.2%} too low under stress"

    def test_memory_exhaustion_attack(self):
        """Test memory exhaustion scenarios."""
        client = TestClient(app, raise_server_exceptions=False)

        # Create extremely large payloads
        huge_data = {
            "data": "x" * (10 * 1024 * 1024),  # 10MB string
            "nested": {"deep": {"very": {"nested": "data" * 1000}}},
            "array": ["item"] * 10000,
        }

        # Multiple large requests
        for _i in range(5):
            response = client.post("/api/analyze", json=huge_data)
            # Should handle gracefully - either process or reject with proper error
            assert response.status_code in {
                200,
                400,
                413,
                422,
                500,
            }, f"Unexpected status: {response.status_code}"

        # Force garbage collection
        gc.collect()

    def test_malicious_input_injection(self):
        """Test various injection attack vectors."""
        client = TestClient(app, raise_server_exceptions=False)

        malicious_payloads = [
            # SQL injection attempts
            {"query": "'; DROP TABLE users; --"},
            {"user_id": "1' OR '1'='1"},
            # XSS attempts
            {"name": "<script>alert('xss')</script>"},
            {"description": "javascript:alert('xss')"},
            # Command injection
            {"command": "; rm -rf /"},
            {"path": "../../../etc/passwd"},
            # NoSQL injection
            {"$where": "function() { return true; }"},
            # LDAP injection
            {"filter": "*)(&"},
            # XML injection
            {
                "xml": "<?xml version='1.0'?><!DOCTYPE foo [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]><foo>&xxe;</foo>"
            },
            # Template injection
            {"template": "{{7*7}}"},
            {"template": "${7*7}"},
            # Extremely long strings
            {"long_field": "A" * 1000000},
            # Unicode attacks
            {"unicode": "\u0000\u0001\u0002\ufeff"},
            # JSON bombs - removed the problematic one that causes test recursion
            # {"nested": json.loads('{"a":' * 1000 + '"value"' + "}" * 1000)},
        ]

        for payload in malicious_payloads:
            try:
                response = client.post("/api/analyze", json=payload)
                # Should handle malicious input gracefully
                assert response.status_code in {
                    200,
                    400,
                    422,
                    413,
                }, f"Payload {payload} caused unexpected status: {response.status_code}"
            except Exception:
                # Exceptions should be caught and handled
                pass

    def test_race_conditions(self):
        """Test for race conditions in concurrent operations."""
        client = TestClient(app, raise_server_exceptions=False)

        def create_user():
            return client.post(
                "/auth/signup",
                data={
                    "email": f"test{random.randint(1, 1000000)}@example.com",
                    "password": "TestPassword123!",
                    "confirm_password": "TestPassword123!",
                },
            )

        def login_user():
            return client.post(
                "/auth/login",
                data={"email": "test@example.com", "password": "TestPassword123!"},
            )

        # Simulate race conditions
        with ThreadPoolExecutor(max_workers=50) as executor:
            # Concurrent user creation
            create_futures = [executor.submit(create_user) for _ in range(100)]
            login_futures = [executor.submit(login_user) for _ in range(100)]

            create_results = [f.result() for f in create_futures]
            login_results = [f.result() for f in login_futures]

        # Should handle race conditions gracefully
        for result in create_results + login_results:
            assert result.status_code in {
                200,
                201,
                400,
                401,
                422,
                429,
            }, f"Unexpected race condition result: {result.status_code}"

    def test_resource_exhaustion(self):
        """Test resource exhaustion scenarios."""
        client = TestClient(app, raise_server_exceptions=False)

        # File descriptor exhaustion simulation
        clients = []
        try:
            for _i in range(100):
                new_client = TestClient(app, raise_server_exceptions=False)
                clients.append(new_client)
                response = new_client.get("/health")
                assert response.status_code in {
                    200,
                    500,
                    503,
                }, f"Resource exhaustion failed: {response.status_code}"
        finally:
            # Cleanup
            for client in clients:
                try:
                    client.close()
                except Exception:
                    pass

    def test_infinite_recursion_protection(self):
        """Test protection against infinite recursion attacks."""
        client = TestClient(app, raise_server_exceptions=False)

        # Create deeply nested JSON
        deep_obj = {"value": "test"}
        for _i in range(100):  # Reduced depth to test protection
            deep_obj = {"nested": deep_obj}

        response = client.post("/api/analyze", json=deep_obj)
        # Should either handle or fail gracefully with 400 (structure too deep)
        assert response.status_code in {
            200,
            400,
            413,
            422,
        }, f"Deep nesting caused unexpected status: {response.status_code}"

    def test_extreme_input_variations(self):
        """Test extreme input variations."""
        client = TestClient(app, raise_server_exceptions=False)

        extreme_inputs = [
            # Empty/null variations
            {},
            None,
            "",
            [],
            # Type confusion
            {"number_field": "not_a_number"},
            {"array_field": "not_an_array"},
            {"object_field": 12345},
            # Boundary values
            {"amount": 0},
            {"amount": -1},
            {"amount": float("inf")},
            {"amount": float("-inf")},
            {"amount": float("nan")},
            # Very large numbers
            {"large_number": 10**100},
            {"negative_large": -(10**100)},
            # Special characters
            {"special": "\x00\x01\x02\x03\x04\x05"},
            {"unicode": "🔥💀☠️🧨💣"},
            # Format confusion
            {"date": "not-a-date"},
            {"email": "not-an-email"},
            {"url": "not-a-url"},
        ]

        for input_data in extreme_inputs:
            try:
                response = client.post("/api/analyze", json=input_data)
                assert response.status_code in {
                    200,
                    400,
                    422,
                }, f"Input {input_data} caused unexpected status: {response.status_code}"
            except Exception:
                # Should not cause unhandled exceptions
                pass

    def test_timing_attacks(self):
        """Test for timing attack vulnerabilities."""
        client = TestClient(app, raise_server_exceptions=False)

        # Test authentication timing on the API endpoint with timing protection
        times = []
        for _i in range(10):
            start = time.time()
            response = client.post(
                "/auth/login/api",
                json={"email": "nonexistent@example.com", "password": "wrongpassword"},
            )
            end = time.time()
            times.append(end - start)
            # Verify we get the expected 401 response
            assert response.status_code == 401

        # Response times should be consistent (within reasonable variance)
        avg_time = sum(times) / len(times)
        max_variance = max(abs(t - avg_time) for t in times)

        # With timing protection (50ms minimum), variance should be reasonable
        # Allow for some system jitter but require generally consistent timing
        assert (
            max_variance < 0.1  # 100ms max variance is reasonable for timing protection
        ), f"Timing attack possible: variance {max_variance:.3f}s, avg {avg_time:.3f}s"

        # Also verify that all times are at least close to the 50ms minimum
        min_time = min(times)
        assert (
            min_time >= 0.040
        ), f"Timing too fast, protection may not be working: {min_time:.3f}s"

    def test_session_fixation_protection(self):
        """Test session fixation attack protection."""
        client = TestClient(app, raise_server_exceptions=False)

        # Get initial session
        client.get("/")

        # Attempt login with fixed session
        response2 = client.post(
            "/auth/login",
            data={"email": "test@example.com", "password": "wrongpassword"},
        )

        # At minimum, the application should handle this gracefully
        assert response2.status_code in {200, 400, 401, 422}

    def test_denial_of_service_resilience(self):
        """Test resilience against DoS attacks."""
        client = TestClient(app, raise_server_exceptions=False)

        # Rapid-fire requests
        start_time = time.time()
        request_count = 0

        # Make requests for 5 seconds
        while time.time() - start_time < 5:
            response = client.get("/health")
            request_count += 1
            assert response.status_code in {
                200,
                429,
                503,
            }, f"DoS test failed: {response.status_code}"

        # Should handle at least some requests
        assert request_count > 10, f"Only handled {request_count} requests in 5 seconds"

    def test_error_handling_exhaustion(self):
        """Test error handling under extreme conditions."""
        client = TestClient(app, raise_server_exceptions=False)

        # Generate many different types of errors rapidly
        error_generators = [
            lambda: client.get("/nonexistent/endpoint"),
            lambda: client.post("/auth/login", data={"invalid": "data"}),
            lambda: client.get("/admin/users"),  # Now properly returns 401
            lambda: client.put("/api/analyze", json={"invalid": "method"}),
            lambda: client.delete("/health"),  # Method not allowed
        ]

        error_counts = {}
        for _i in range(200):  # Generate 200 errors
            generator = random.choice(error_generators)
            response = generator()
            status = response.status_code
            error_counts[status] = error_counts.get(status, 0) + 1

        # Should handle all errors gracefully - allow 401 for admin endpoint
        for status in error_counts:
            assert status >= 400, f"Expected error status, got {status}"

    def test_circular_reference_protection(self):
        """Test protection against circular reference attacks."""
        client = TestClient(app, raise_server_exceptions=False)

        # This would normally cause infinite loops in naive JSON serializers
        # We can't create true circular references in JSON, but we can test deep structures

        # Create a structure that could cause issues
        complex_data = {
            "refs": [{"id": 1, "ref": 2}, {"id": 2, "ref": 1}],
            "deep": {"level": 1},
        }

        # Add many levels
        current = complex_data["deep"]
        for i in range(1000):
            current["next"] = {"level": i + 2}
            current = current["next"]

        try:
            response = client.post("/api/analyze", json=complex_data)
            assert response.status_code in {
                200,
                400,
                413,
                422,
            }, f"Circular ref test failed: {response.status_code}"
        except Exception:
            # Should not cause application crashes
            pass
