"""Performance and Load Tests
Tests application performance under various load conditions.
"""

import asyncio
import time
from statistics import mean, median

import pytest


class TestPerformanceBenchmarks:
    """Test performance benchmarks for critical operations."""

    @pytest.mark.asyncio
    async def test_authentication_performance(self, async_client) -> None:
        """Test authentication endpoint performance."""
        start_time = time.time()

        tasks = []
        for i in range(10):
            task = async_client.post(
                "/auth/login",
                data={"username": f"user{i}@example.com", "password": "testpassword"},
            )
            tasks.append(task)

        await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        total_time = end_time - start_time
        avg_response_time = total_time / len(tasks)

        # Performance assertions
        assert avg_response_time < 0.5  # Average response time under 500ms
        assert total_time < 2.0  # Total time for 10 requests under 2 seconds

    @pytest.mark.asyncio
    async def test_transaction_processing_performance(self, async_client) -> None:
        """Test transaction processing performance."""
        transaction_times = []

        for i in range(20):
            start_time = time.time()

            await async_client.post(
                "/transactions",
                json={
                    "amount": 100.0 + i,
                    "currency": "USD",
                    "recipient": f"recipient_{i}",
                    "description": f"Performance test transaction {i}",
                },
            )

            end_time = time.time()
            transaction_times.append(end_time - start_time)

        avg_time = mean(transaction_times)
        median_time = median(transaction_times)
        max_time = max(transaction_times)

        # Performance assertions
        assert avg_time < 1.0  # Average processing time under 1 second
        assert median_time < 0.8  # Median processing time under 800ms
        assert max_time < 2.0  # Maximum processing time under 2 seconds

    @pytest.mark.asyncio
    async def test_compliance_analysis_performance(self, async_client) -> None:
        """Test compliance analysis performance."""
        large_transaction_data = {
            "amount": 50000,
            "currency": "USD",
            "recipient": "complex_entity",
            "description": "Large complex transaction for performance testing",
            "metadata": {
                "source": "api",
                "complexity": "high",
                "additional_data": ["tag1", "tag2", "tag3"] * 100,  # Large metadata
            },
        }

        start_time = time.time()
        response = await async_client.post("/transactions", json=large_transaction_data)
        end_time = time.time()

        processing_time = end_time - start_time

        # Performance assertions
        assert response.status_code == 201
        assert processing_time < 3.0  # Complex analysis should complete under 3 seconds


class TestConcurrencyAndScaling:
    """Test application behavior under concurrent load."""

    @pytest.mark.asyncio
    async def test_concurrent_user_sessions(self, async_client) -> None:
        """Test handling of concurrent user sessions."""
        concurrent_users = 50
        requests_per_user = 5

        async def user_session(user_id: int):
            """Simulate a user session with multiple requests."""
            session_times = []

            for request_num in range(requests_per_user):
                start_time = time.time()

                # Simulate various user actions
                if request_num == 0:
                    # Login
                    await async_client.post(
                        "/auth/login",
                        data={
                            "username": f"user{user_id}@example.com",
                            "password": "testpassword",
                        },
                    )
                elif request_num == 1:
                    # View dashboard
                    await async_client.get("/dashboard")
                elif request_num == 2:
                    # Create transaction
                    await async_client.post(
                        "/transactions",
                        json={
                            "amount": 100.0,
                            "currency": "USD",
                            "recipient": "test_recipient",
                        },
                    )
                else:
                    # View transactions
                    await async_client.get("/transactions")

                end_time = time.time()
                session_times.append(end_time - start_time)

            return session_times

        # Run concurrent user sessions
        start_time = time.time()
        tasks = [user_session(i) for i in range(concurrent_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        total_time = end_time - start_time

        # Calculate performance metrics
        all_times = []
        for result in results:
            if isinstance(result, list):
                all_times.extend(result)

        if all_times:
            avg_response_time = mean(all_times)
            max_response_time = max(all_times)

            # Performance assertions
            assert avg_response_time < 1.0  # Average response time under 1 second
            assert max_response_time < 5.0  # Maximum response time under 5 seconds
            assert total_time < 30.0  # Total test time under 30 seconds

    @pytest.mark.asyncio
    async def test_database_connection_pooling(self, async_client) -> None:
        """Test database connection pooling under load."""
        concurrent_db_operations = 100

        async def database_operation(operation_id: int):
            """Simulate database-intensive operation."""
            start_time = time.time()

            # Create transaction (database write)
            response = await async_client.post(
                "/transactions",
                json={
                    "amount": float(operation_id),
                    "currency": "USD",
                    "recipient": f"db_test_{operation_id}",
                },
            )

            if response.status_code == 201:
                transaction_id = response.json()["id"]

                # Read transaction back (database read)
                read_response = await async_client.get(
                    f"/transactions/{transaction_id}",
                )

                end_time = time.time()
                return {
                    "success": read_response.status_code == 200,
                    "time": end_time - start_time,
                }

            return {"success": False, "time": time.time() - start_time}

        # Run concurrent database operations
        tasks = [database_operation(i) for i in range(concurrent_db_operations)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze results
        successful_operations = [
            r for r in results if isinstance(r, dict) and r["success"]
        ]
        operation_times = [r["time"] for r in successful_operations]

        success_rate = len(successful_operations) / len(results)
        avg_db_time = mean(operation_times) if operation_times else 0

        # Performance assertions
        assert success_rate > 0.95  # At least 95% success rate
        assert avg_db_time < 2.0  # Average database operation under 2 seconds


class TestMemoryAndResourceUsage:
    """Test memory usage and resource consumption."""

    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, async_client) -> None:
        """Test memory usage during high-load operations."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Perform memory-intensive operations
        large_data_operations = []
        for i in range(100):
            # Create transactions with large metadata
            large_data = {
                "amount": 1000.0,
                "currency": "USD",
                "recipient": f"memory_test_{i}",
                "metadata": {
                    "large_field": "x" * 10000,  # 10KB of data
                    "array_data": list(range(1000)),
                },
            }

            task = async_client.post("/transactions", json=large_data)
            large_data_operations.append(task)

        # Execute all operations
        await asyncio.gather(*large_data_operations)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory usage assertions
        assert memory_increase < 100  # Memory increase should be less than 100MB
        assert final_memory < 500  # Total memory usage should be reasonable

    def test_cpu_usage_monitoring(self) -> None:
        """Test CPU usage during intensive operations."""
        import psutil

        # Monitor CPU usage
        cpu_percentages = []

        def cpu_monitor() -> None:
            for _ in range(10):
                cpu_percentages.append(psutil.cpu_percent(interval=1))

        # Run CPU monitoring in background
        import threading

        monitor_thread = threading.Thread(target=cpu_monitor)
        monitor_thread.start()

        # Perform CPU-intensive operations
        for _i in range(1000):
            # Simulate complex calculations
            sum(j**2 for j in range(100))

        monitor_thread.join()

        avg_cpu = mean(cpu_percentages)
        max_cpu = max(cpu_percentages)

        # CPU usage should be reasonable
        assert avg_cpu < 80  # Average CPU usage under 80%
        assert max_cpu < 95  # Maximum CPU usage under 95%


class TestScalabilityLimits:
    """Test application scalability limits."""

    @pytest.mark.asyncio
    async def test_maximum_concurrent_requests(self, async_client) -> None:
        """Test maximum number of concurrent requests the system can handle."""
        max_concurrent = 200
        request_timeout = 10  # seconds

        async def make_request(request_id: int):
            """Make a single request with timeout."""
            try:
                start_time = time.time()
                response = await asyncio.wait_for(
                    async_client.get("/health"),
                    timeout=request_timeout,
                )
                end_time = time.time()

                return {
                    "success": response.status_code == 200,
                    "time": end_time - start_time,
                    "request_id": request_id,
                }
            except TimeoutError:
                return {
                    "success": False,
                    "time": request_timeout,
                    "request_id": request_id,
                    "error": "timeout",
                }
            except Exception as e:
                return {
                    "success": False,
                    "time": 0,
                    "request_id": request_id,
                    "error": str(e),
                }

        # Run maximum concurrent requests
        tasks = [make_request(i) for i in range(max_concurrent)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze results
        successful_requests = [
            r for r in results if isinstance(r, dict) and r["success"]
        ]
        [r for r in results if isinstance(r, dict) and not r["success"]]

        success_rate = len(successful_requests) / len(results)
        avg_response_time = (
            mean([r["time"] for r in successful_requests]) if successful_requests else 0
        )

        # Scalability assertions
        assert success_rate > 0.90  # At least 90% success rate under max load
        assert avg_response_time < 5.0  # Average response time under 5 seconds
