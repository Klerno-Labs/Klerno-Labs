"""Performance benchmarking tests for the API."""

import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestPerformanceBenchmarks:
    """Performance benchmark tests."""

    def test_health_endpoint_performance(self, client) -> None:
        """Benchmark health endpoint performance."""
        # Warmup
        for _ in range(5):
            client.get("/healthz")

        # Measure performance
        response_times = []
        for _ in range(100):
            start_time = time.perf_counter()
            response = client.get("/healthz")
            end_time = time.perf_counter()

            assert response.status_code == 200
            response_times.append((end_time - start_time) * 1000)  # Convert to ms

        # Calculate statistics
        avg_time = statistics.mean(response_times)
        statistics.median(response_times)
        p95_time = sorted(response_times)[int(len(response_times) * 0.95)]

        # Performance assertions
        assert avg_time < 100, f"Average response time too high: {avg_time:.2f}ms"
        assert p95_time < 500, f"95th percentile too high: {p95_time:.2f}ms"

    def test_concurrent_request_performance(self, client) -> None:
        """Benchmark concurrent request performance."""
        num_workers = 10
        requests_per_worker = 20
        total_requests = num_workers * requests_per_worker

        def make_requests(worker_id):
            """Make multiple requests from a single worker."""
            worker_times = []
            for _ in range(requests_per_worker):
                start_time = time.perf_counter()
                response = client.get("/healthz")
                end_time = time.perf_counter()

                assert response.status_code == 200
                worker_times.append((end_time - start_time) * 1000)

            return worker_times

        # Execute concurrent requests
        start_time = time.perf_counter()

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(make_requests, worker_id)
                for worker_id in range(num_workers)
            ]

            all_times = []
            for future in as_completed(futures):
                worker_times = future.result()
                all_times.extend(worker_times)

        total_time = time.perf_counter() - start_time

        # Calculate throughput and statistics
        throughput = total_requests / total_time
        avg_time = statistics.mean(all_times)
        sorted(all_times)[int(len(all_times) * 0.95)]

        # Performance assertions
        assert throughput > 50, f"Throughput too low: {throughput:.2f} req/s"
        assert avg_time < 200, f"Average response time too high: {avg_time:.2f}ms"

    def test_memory_efficiency(self, client) -> None:
        """Test memory efficiency under load."""
        import gc

        # Get initial memory usage (rough estimate)
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Make many requests
        for _ in range(1000):
            response = client.get("/healthz")
            assert response.status_code == 200

        # Check memory usage after
        gc.collect()
        final_objects = len(gc.get_objects())

        object_growth = final_objects - initial_objects

        # Should not have excessive object growth
        assert object_growth < 10000, f"Too many objects created: {object_growth}"

    def test_database_operation_performance(self, client) -> None:
        """Test database operation performance."""
        # Test endpoints that might involve database operations
        endpoints = [
            ("/health", "GET"),
            ("/status", "GET"),
        ]

        results = {}

        for endpoint, method in endpoints:
            response_times = []

            # Warmup
            for _ in range(3):
                if method == "GET":
                    client.get(endpoint)

            # Measure
            for _ in range(50):
                start_time = time.perf_counter()
                if method == "GET":
                    response = client.get(endpoint)
                end_time = time.perf_counter()

                if response.status_code == 200:
                    response_times.append((end_time - start_time) * 1000)

            if response_times:
                avg_time = statistics.mean(response_times)
                results[endpoint] = avg_time

        for endpoint, avg_time in results.items():
            # Database operations should be reasonably fast
            assert avg_time < 1000, f"{endpoint} too slow: {avg_time:.2f}ms"

    def test_api_response_size_efficiency(self, client) -> None:
        """Test API response size efficiency."""
        endpoints = ["/healthz", "/status", "/health"]

        for endpoint in endpoints:
            response = client.get(endpoint)
            if response.status_code == 200:
                response_size = len(response.content)
                (
                    response.json()
                    if response.headers.get("content-type", "").startswith(
                        "application/json",
                    )
                    else {}
                )

                # Response sizes should be reasonable
                assert response_size < 10000, (
                    f"{endpoint} response too large: {response_size} bytes"
                )

    def test_cold_start_performance(self, client) -> None:
        """Test cold start performance (first request after initialization)."""
        # Create a fresh client to simulate cold start
        fresh_client = TestClient(app)

        start_time = time.perf_counter()
        response = fresh_client.get("/healthz")
        cold_start_time = (time.perf_counter() - start_time) * 1000

        assert response.status_code == 200

        # Cold start should not be excessive
        assert cold_start_time < 5000, f"Cold start too slow: {cold_start_time:.2f}ms"


def generate_performance_report():
    """Generate a comprehensive performance report."""
    client = TestClient(app)

    # Run quick performance tests
    start_time = time.perf_counter()
    for _ in range(10):
        response = client.get("/healthz")
        assert response.status_code == 200
    return ((time.perf_counter() - start_time) / 10) * 1000


if __name__ == "__main__":
    generate_performance_report()
