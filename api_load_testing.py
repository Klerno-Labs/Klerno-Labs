#!/usr/bin/env python3
"""
KLERNO LABS ENTERPRISE PLATFORM - API LOAD TESTING FRAMEWORK
=============================================================

Comprehensive API load testing with concurrent requests, performance benchmarking,
and enterprise-grade validation for production readiness.
"""

import asyncio
import concurrent.futures
import json
import logging
import statistics
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from queue import Queue
from typing import Any, Dict, List, Optional, Tuple

import aiohttp


@dataclass
class LoadTestConfig:
    """Configuration for load testing parameters"""

    base_url: str = "http://127.0.0.1:8000"
    concurrent_users: int = 50
    requests_per_user: int = 20
    ramp_up_time: int = 10  # seconds
    test_duration: int = 60  # seconds
    request_timeout: int = 10  # seconds
    think_time: float = 0.1  # seconds between requests


@dataclass
class RequestResult:
    """Result of a single API request"""

    endpoint: str
    method: str
    status_code: int
    response_time: float
    timestamp: str
    user_id: int
    success: bool
    error_message: Optional[str] = None
    response_size: int = 0


@dataclass
class LoadTestResults:
    """Comprehensive load test results"""

    test_name: str
    config: LoadTestConfig
    start_time: str
    end_time: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time: float
    min_response_time: float
    max_response_time: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    error_rate: float
    endpoint_results: Dict[str, Any]
    raw_results: List[RequestResult]


class APILoadTester:
    """Enterprise-grade API load testing framework"""

    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.logger = self._setup_logging()
        self.results_queue = Queue()
        self.test_scenarios = self._define_test_scenarios()

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for load testing"""
        log_file = Path("logs/api_load_testing.log")
        log_file.parent.mkdir(exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
        )
        return logging.getLogger("APILoadTester")

    def _define_test_scenarios(self) -> List[Dict[str, Any]]:
        """Define comprehensive test scenarios for enterprise endpoints"""
        return [
            # Core health endpoints
            {"method": "GET", "endpoint": "/health", "weight": 20},
            {"method": "GET", "endpoint": "/status", "weight": 15},
            {"method": "GET", "endpoint": "/docs", "weight": 10},
            {"method": "GET", "endpoint": "/openapi.json", "weight": 5},
            # Enterprise endpoints
            {"method": "GET", "endpoint": "/enterprise/status", "weight": 15},
            {"method": "GET", "endpoint": "/enterprise/health", "weight": 10},
            {"method": "GET", "endpoint": "/enterprise/metrics", "weight": 10},
            {"method": "GET", "endpoint": "/enterprise/analytics", "weight": 8},
            # API endpoints
            {"method": "GET", "endpoint": "/api/v1/health", "weight": 5},
            {"method": "GET", "endpoint": "/api/v1/status", "weight": 5},
            {"method": "GET", "endpoint": "/api/analytics/dashboard", "weight": 3},
            {"method": "GET", "endpoint": "/api/monitoring/metrics", "weight": 2},
            # Root endpoint
            {"method": "GET", "endpoint": "/", "weight": 2},
        ]

    def _select_random_scenario(self) -> Dict[str, Any]:
        """Select a random test scenario based on weights"""
        import random

        total_weight = sum(scenario["weight"] for scenario in self.test_scenarios)
        rand_value = random.randint(1, total_weight)

        current_weight = 0
        for scenario in self.test_scenarios:
            current_weight += scenario["weight"]
            if rand_value <= current_weight:
                return scenario

        # Fallback to first scenario
        return self.test_scenarios[0]

    async def make_request(
        self, session: aiohttp.ClientSession, scenario: Dict[str, Any], user_id: int
    ) -> RequestResult:
        """Make a single API request and return result"""
        method = scenario["method"]
        endpoint = scenario["endpoint"]
        url = f"{self.config.base_url}{endpoint}"

        start_time = time.time()
        timestamp = datetime.now().isoformat()

        try:
            timeout = aiohttp.ClientTimeout(total=self.config.request_timeout)
            async with session.request(method, url, timeout=timeout) as response:
                await response.read()  # Ensure response is fully consumed
                response_time = time.time() - start_time

                return RequestResult(
                    endpoint=endpoint,
                    method=method,
                    status_code=response.status,
                    response_time=response_time,
                    timestamp=timestamp,
                    user_id=user_id,
                    success=response.status == 200,
                    response_size=response.content_length or 0,
                )

        except Exception as e:
            response_time = time.time() - start_time
            return RequestResult(
                endpoint=endpoint,
                method=method,
                status_code=0,
                response_time=response_time,
                timestamp=timestamp,
                user_id=user_id,
                success=False,
                error_message=str(e),
            )

    async def simulate_user(
        self, user_id: int, session: aiohttp.ClientSession
    ) -> List[RequestResult]:
        """Simulate a single user making multiple requests"""
        results = []

        try:
            for request_num in range(self.config.requests_per_user):
                # Select random scenario
                scenario = self._select_random_scenario()

                # Make request
                result = await self.make_request(session, scenario, user_id)
                results.append(result)

                # Think time between requests
                if request_num < self.config.requests_per_user - 1:
                    await asyncio.sleep(self.config.think_time)

        except Exception as e:
            self.logger.error(f"User {user_id} simulation error: {e}")

        return results

    async def run_load_test(
        self, test_name: str = "Enterprise API Load Test"
    ) -> LoadTestResults:
        """Run comprehensive load test with concurrent users"""
        self.logger.info(f"Starting load test: {test_name}")
        start_time = datetime.now()
        all_results = []

        # Create connector with connection pooling
        connector = aiohttp.TCPConnector(
            limit=self.config.concurrent_users * 2,
            limit_per_host=self.config.concurrent_users,
            keepalive_timeout=30,
        )

        async with aiohttp.ClientSession(connector=connector) as session:
            # Create tasks for concurrent users
            tasks = []

            # Gradual ramp-up of users
            users_per_batch = max(1, self.config.concurrent_users // 10)
            ramp_up_delay = self.config.ramp_up_time / 10

            for batch in range(0, self.config.concurrent_users, users_per_batch):
                batch_tasks = []
                for user_id in range(
                    batch, min(batch + users_per_batch, self.config.concurrent_users)
                ):
                    task = asyncio.create_task(self.simulate_user(user_id, session))
                    batch_tasks.append(task)
                    tasks.append(task)

                self.logger.info(
                    f"Started batch of {len(batch_tasks)} users (total: {len(tasks)})"
                )

                # Ramp-up delay
                if batch + users_per_batch < self.config.concurrent_users:
                    await asyncio.sleep(ramp_up_delay)

            # Wait for all users to complete
            self.logger.info(
                f"All {self.config.concurrent_users} users started. Waiting for completion..."
            )

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Flatten results
            for user_results in batch_results:
                if isinstance(user_results, list):
                    all_results.extend(user_results)
                else:
                    self.logger.error(f"User simulation failed: {user_results}")

        end_time = datetime.now()

        # Analyze results
        return self._analyze_results(test_name, all_results, start_time, end_time)

    def _analyze_results(
        self,
        test_name: str,
        results: List[RequestResult],
        start_time: datetime,
        end_time: datetime,
    ) -> LoadTestResults:
        """Analyze load test results and generate comprehensive report"""
        if not results:
            self.logger.error("No results to analyze")
            return None

        # Basic statistics
        total_requests = len(results)
        successful_requests = sum(1 for r in results if r.success)
        failed_requests = total_requests - successful_requests

        # Response time statistics
        response_times = [r.response_time for r in results]
        average_response_time = statistics.mean(response_times)
        min_response_time = min(response_times)
        max_response_time = max(response_times)

        # Percentiles
        p50_response_time = statistics.median(response_times)
        p95_response_time = self._percentile(response_times, 95)
        p99_response_time = self._percentile(response_times, 99)

        # Throughput
        test_duration = (end_time - start_time).total_seconds()
        requests_per_second = total_requests / test_duration if test_duration > 0 else 0

        # Error rate
        error_rate = (failed_requests / total_requests) * 100

        # Endpoint-specific analysis
        endpoint_results = self._analyze_by_endpoint(results)

        return LoadTestResults(
            test_name=test_name,
            config=self.config,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            average_response_time=average_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p50_response_time=p50_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            requests_per_second=requests_per_second,
            error_rate=error_rate,
            endpoint_results=endpoint_results,
            raw_results=results,
        )

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile value"""
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)

        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower_index = int(index)
            upper_index = lower_index + 1
            weight = index - lower_index
            return (
                sorted_data[lower_index] * (1 - weight)
                + sorted_data[upper_index] * weight
            )

    def _analyze_by_endpoint(self, results: List[RequestResult]) -> Dict[str, Any]:
        """Analyze results grouped by endpoint"""
        endpoint_data = {}

        for result in results:
            endpoint = result.endpoint
            if endpoint not in endpoint_data:
                endpoint_data[endpoint] = []
            endpoint_data[endpoint].append(result)

        endpoint_analysis = {}
        for endpoint, endpoint_results in endpoint_data.items():
            total = len(endpoint_results)
            successful = sum(1 for r in endpoint_results if r.success)
            failed = total - successful

            response_times = [r.response_time for r in endpoint_results]
            avg_response_time = statistics.mean(response_times)
            max_response_time = max(response_times)

            endpoint_analysis[endpoint] = {
                "total_requests": total,
                "successful_requests": successful,
                "failed_requests": failed,
                "success_rate": (successful / total) * 100,
                "average_response_time": avg_response_time,
                "max_response_time": max_response_time,
                "min_response_time": min(response_times),
            }

        return endpoint_analysis

    def export_results(
        self, results: LoadTestResults, filename: str = "load_test_results.json"
    ):
        """Export load test results to JSON file"""
        if not results:
            self.logger.error("No results to export")
            return

        # Convert to dict and handle non-serializable objects
        export_data = {
            "test_summary": {
                "test_name": results.test_name,
                "start_time": results.start_time,
                "end_time": results.end_time,
                "config": asdict(results.config),
                "total_requests": results.total_requests,
                "successful_requests": results.successful_requests,
                "failed_requests": results.failed_requests,
                "error_rate": results.error_rate,
                "requests_per_second": results.requests_per_second,
            },
            "performance_metrics": {
                "average_response_time": results.average_response_time,
                "min_response_time": results.min_response_time,
                "max_response_time": results.max_response_time,
                "p50_response_time": results.p50_response_time,
                "p95_response_time": results.p95_response_time,
                "p99_response_time": results.p99_response_time,
            },
            "endpoint_analysis": results.endpoint_results,
            "raw_results": [asdict(r) for r in results.raw_results],
        }

        with open(filename, "w") as f:
            json.dump(export_data, f, indent=2)

        self.logger.info(f"Load test results exported to {filename}")

    def generate_report(self, results: LoadTestResults):
        """Generate comprehensive load test report"""
        if not results:
            print("❌ No results to report")
            return

        print(f"\n🚀 KLERNO LABS API LOAD TEST REPORT")
        print("=" * 60)
        print(f"Test Name: {results.test_name}")
        print(f"Test Period: {results.start_time} to {results.end_time}")

        # Test configuration
        print(f"\n⚙️  TEST CONFIGURATION")
        print("-" * 30)
        print(f"Base URL: {results.config.base_url}")
        print(f"Concurrent Users: {results.config.concurrent_users}")
        print(f"Requests per User: {results.config.requests_per_user}")
        print(f"Ramp-up Time: {results.config.ramp_up_time}s")
        print(f"Request Timeout: {results.config.request_timeout}s")

        # Overall results
        print(f"\n📊 OVERALL RESULTS")
        print("-" * 30)
        print(f"Total Requests: {results.total_requests:,}")
        print(f"Successful Requests: {results.successful_requests:,}")
        print(f"Failed Requests: {results.failed_requests:,}")
        print(
            f"Success Rate: {((results.successful_requests / results.total_requests) * 100):.2f}%"
        )
        print(f"Error Rate: {results.error_rate:.2f}%")
        print(f"Requests per Second: {results.requests_per_second:.2f}")

        # Performance metrics
        print(f"\n⚡ PERFORMANCE METRICS")
        print("-" * 30)
        print(f"Average Response Time: {results.average_response_time:.3f}s")
        print(f"Minimum Response Time: {results.min_response_time:.3f}s")
        print(f"Maximum Response Time: {results.max_response_time:.3f}s")
        print(f"50th Percentile (P50): {results.p50_response_time:.3f}s")
        print(f"95th Percentile (P95): {results.p95_response_time:.3f}s")
        print(f"99th Percentile (P99): {results.p99_response_time:.3f}s")

        # Endpoint analysis
        print(f"\n🎯 ENDPOINT PERFORMANCE")
        print("-" * 50)
        for endpoint, stats in results.endpoint_results.items():
            status_icon = (
                "✅"
                if stats["success_rate"] >= 95
                else "⚠️" if stats["success_rate"] >= 90 else "❌"
            )
            print(f"{status_icon} {endpoint}")
            print(
                f"   Requests: {stats['total_requests']:,} | Success Rate: {stats['success_rate']:.1f}%"
            )
            print(
                f"   Avg Time: {stats['average_response_time']:.3f}s | Max Time: {stats['max_response_time']:.3f}s"
            )

        # Performance assessment
        print(f"\n🎯 PERFORMANCE ASSESSMENT")
        print("-" * 30)

        if results.error_rate < 1:
            print("✅ Excellent error rate (< 1%)")
        elif results.error_rate < 5:
            print("⚠️  Acceptable error rate (< 5%)")
        else:
            print("❌ High error rate (≥ 5%)")

        if results.average_response_time < 0.1:
            print("✅ Excellent response time (< 100ms)")
        elif results.average_response_time < 0.5:
            print("⚠️  Good response time (< 500ms)")
        else:
            print("❌ Slow response time (≥ 500ms)")

        if results.requests_per_second > 100:
            print("✅ High throughput (> 100 RPS)")
        elif results.requests_per_second > 50:
            print("⚠️  Moderate throughput (> 50 RPS)")
        else:
            print("❌ Low throughput (≤ 50 RPS)")


def run_comprehensive_load_tests():
    """Run a suite of comprehensive load tests"""
    print("🚀 KLERNO LABS COMPREHENSIVE API LOAD TESTING SUITE")
    print("=" * 60)

    # Test configurations
    test_configs = [
        {
            "name": "Light Load Test",
            "config": LoadTestConfig(
                concurrent_users=10,
                requests_per_user=10,
                ramp_up_time=5,
                test_duration=30,
            ),
        },
        {
            "name": "Moderate Load Test",
            "config": LoadTestConfig(
                concurrent_users=25,
                requests_per_user=15,
                ramp_up_time=10,
                test_duration=45,
            ),
        },
        {
            "name": "Heavy Load Test",
            "config": LoadTestConfig(
                concurrent_users=50,
                requests_per_user=20,
                ramp_up_time=15,
                test_duration=60,
            ),
        },
    ]

    all_results = []

    for i, test_spec in enumerate(test_configs, 1):
        print(f"\n🎯 Running Test {i}/3: {test_spec['name']}")
        print("-" * 40)

        tester = APILoadTester(test_spec["config"])

        try:
            # Run the load test
            results = asyncio.run(tester.run_load_test(test_spec["name"]))

            if results:
                # Generate report
                tester.generate_report(results)

                # Export results
                filename = (
                    f"load_test_{i}_{test_spec['name'].lower().replace(' ', '_')}.json"
                )
                tester.export_results(results, filename)

                all_results.append(results)
            else:
                print(f"❌ Test {i} failed to produce results")

        except Exception as e:
            print(f"❌ Test {i} failed with error: {e}")

        # Brief pause between tests
        if i < len(test_configs):
            print(f"\n⏳ Waiting 10 seconds before next test...")
            time.sleep(10)

    # Summary report
    print(f"\n📋 COMPREHENSIVE LOAD TESTING SUMMARY")
    print("=" * 50)

    for i, results in enumerate(all_results, 1):
        config_name = test_configs[i - 1]["name"]
        print(f"\n{i}. {config_name}:")
        print(f"   Total Requests: {results.total_requests:,}")
        print(
            f"   Success Rate: {((results.successful_requests / results.total_requests) * 100):.1f}%"
        )
        print(f"   Avg Response Time: {results.average_response_time:.3f}s")
        print(f"   Throughput: {results.requests_per_second:.1f} RPS")

    print(f"\n✅ Load testing completed. Results exported to JSON files.")


async def main():
    """Main function for API load testing"""
    await asyncio.gather(asyncio.to_thread(run_comprehensive_load_tests))


if __name__ == "__main__":
    # Run comprehensive load tests
    run_comprehensive_load_tests()
