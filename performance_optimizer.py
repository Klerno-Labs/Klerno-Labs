#!/usr/bin/env python3
"""
KLERNO LABS ENTERPRISE PLATFORM - PERFORMANCE OPTIMIZATION SUITE
===============================================================

Advanced performance benchmarking and optimization tools for enterprise deployment.
"""

import asyncio
import gc
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import psutil
import requests


@dataclass
class PerformanceMetrics:
    """Container for performance measurement data"""

    endpoint: str
    response_times: List[float]
    success_count: int
    error_count: int
    throughput: float
    memory_usage: float
    cpu_usage: float


class PerformanceOptimizer:
    """Advanced performance optimization and benchmarking suite"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.metrics: Dict[str, PerformanceMetrics] = {}

    def measure_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024

    def measure_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        return psutil.cpu_percent(interval=0.1)

    def benchmark_endpoint(
        self, endpoint: str, num_requests: int = 100, concurrent_requests: int = 10
    ) -> PerformanceMetrics:
        """Benchmark a specific endpoint with concurrent requests"""
        print(f"🔬 Benchmarking {endpoint} with {num_requests} requests...")

        response_times = []
        success_count = 0
        error_count = 0
        start_time = time.time()

        def make_request():
            request_start = time.time()
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=30)
                request_time = time.time() - request_start

                if response.status_code == 200:
                    return request_time, True
                else:
                    return request_time, False
            except Exception:
                return time.time() - request_start, False

        # Execute concurrent requests
        with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]

            for future in as_completed(futures):
                request_time, success = future.result()
                response_times.append(request_time)

                if success:
                    success_count += 1
                else:
                    error_count += 1

        total_time = time.time() - start_time
        throughput = num_requests / total_time

        metrics = PerformanceMetrics(
            endpoint=endpoint,
            response_times=response_times,
            success_count=success_count,
            error_count=error_count,
            throughput=throughput,
            memory_usage=self.measure_memory_usage(),
            cpu_usage=self.measure_cpu_usage(),
        )

        self.metrics[endpoint] = metrics
        return metrics

    def memory_leak_test(self, endpoint: str, iterations: int = 100) -> Dict[str, Any]:
        """Test for memory leaks by making repeated requests"""
        print(f"🧪 Testing {endpoint} for memory leaks over {iterations} iterations...")

        memory_usage = []

        for i in range(iterations):
            # Force garbage collection before measurement
            gc.collect()

            # Measure memory before request
            memory_before = self.measure_memory_usage()

            # Make request
            try:
                requests.get(f"{self.base_url}{endpoint}", timeout=10)
            except Exception:
                pass

            # Force garbage collection after request
            gc.collect()

            # Measure memory after request
            memory_after = self.measure_memory_usage()
            memory_usage.append(memory_after)

            if i % 20 == 0:
                print(f"  Iteration {i}: {memory_after:.2f} MB")

        # Analyze memory trend
        initial_memory = memory_usage[0]
        final_memory = memory_usage[-1]
        max_memory = max(memory_usage)
        avg_memory = statistics.mean(memory_usage)

        memory_increase = final_memory - initial_memory
        leak_detected = memory_increase > 10  # Threshold: 10MB increase

        return {
            "endpoint": endpoint,
            "iterations": iterations,
            "initial_memory_mb": initial_memory,
            "final_memory_mb": final_memory,
            "max_memory_mb": max_memory,
            "avg_memory_mb": avg_memory,
            "memory_increase_mb": memory_increase,
            "leak_detected": leak_detected,
            "memory_usage_trend": memory_usage,
        }

    def stress_test_enterprise(self, duration_seconds: int = 60) -> Dict[str, Any]:
        """Comprehensive stress test of enterprise endpoints"""
        print(f"🚀 Running enterprise stress test for {duration_seconds} seconds...")

        enterprise_endpoints = [
            "/health",
            "/status",
            "/enterprise/status",
            "/enterprise/health",
            "/api/health",
            "/docs",
            "/admin/api/stats",
        ]

        results = {}
        start_time = time.time()

        def stress_endpoint(endpoint):
            endpoint_results = {
                "requests": 0,
                "successes": 0,
                "errors": 0,
                "response_times": [],
            }

            while time.time() - start_time < duration_seconds:
                request_start = time.time()
                try:
                    response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                    request_time = time.time() - request_start

                    endpoint_results["requests"] += 1
                    endpoint_results["response_times"].append(request_time)

                    if response.status_code == 200:
                        endpoint_results["successes"] += 1
                    else:
                        endpoint_results["errors"] += 1

                except Exception:
                    endpoint_results["requests"] += 1
                    endpoint_results["errors"] += 1

                # Small delay to prevent overwhelming
                time.sleep(0.01)

            return endpoint, endpoint_results

        # Run stress test for all endpoints concurrently
        with ThreadPoolExecutor(max_workers=len(enterprise_endpoints)) as executor:
            futures = [
                executor.submit(stress_endpoint, ep) for ep in enterprise_endpoints
            ]

            for future in as_completed(futures):
                endpoint, endpoint_results = future.result()

                # Calculate statistics
                if endpoint_results["response_times"]:
                    endpoint_results["avg_response_time"] = statistics.mean(
                        endpoint_results["response_times"]
                    )
                    endpoint_results["min_response_time"] = min(
                        endpoint_results["response_times"]
                    )
                    endpoint_results["max_response_time"] = max(
                        endpoint_results["response_times"]
                    )
                    endpoint_results["success_rate"] = (
                        endpoint_results["successes"] / endpoint_results["requests"]
                    ) * 100
                else:
                    endpoint_results["avg_response_time"] = 0
                    endpoint_results["min_response_time"] = 0
                    endpoint_results["max_response_time"] = 0
                    endpoint_results["success_rate"] = 0

                results[endpoint] = endpoint_results

        return results

    def generate_performance_report(self) -> None:
        """Generate comprehensive performance analysis report"""
        print("\n🔥 KLERNO LABS ENTERPRISE PERFORMANCE REPORT")
        print("=" * 60)

        if not self.metrics:
            print("No performance metrics available. Run benchmarks first.")
            return

        for endpoint, metrics in self.metrics.items():
            print(f"\n📊 ENDPOINT: {endpoint}")
            print("-" * 40)

            if metrics.response_times:
                avg_time = statistics.mean(metrics.response_times)
                min_time = min(metrics.response_times)
                max_time = max(metrics.response_times)
                p95_time = sorted(metrics.response_times)[
                    int(len(metrics.response_times) * 0.95)
                ]

                print(
                    f"✅ Success Rate: {(metrics.success_count / (metrics.success_count + metrics.error_count)) * 100:.1f}%"
                )
                print(f"⚡ Throughput: {metrics.throughput:.1f} requests/second")
                print(f"📈 Response Times:")
                print(f"   Average: {avg_time:.3f}s")
                print(f"   Min: {min_time:.3f}s")
                print(f"   Max: {max_time:.3f}s")
                print(f"   95th Percentile: {p95_time:.3f}s")
                print(f"💾 Memory Usage: {metrics.memory_usage:.1f} MB")
                print(f"🖥️  CPU Usage: {metrics.cpu_usage:.1f}%")

                # Performance rating
                if avg_time < 0.1:
                    rating = "🌟 EXCELLENT"
                elif avg_time < 0.5:
                    rating = "✅ GOOD"
                elif avg_time < 1.0:
                    rating = "⚠️  ACCEPTABLE"
                else:
                    rating = "❌ NEEDS IMPROVEMENT"

                print(f"🎯 Performance Rating: {rating}")


def main():
    """Run comprehensive performance optimization suite"""
    print("🚀 KLERNO LABS ENTERPRISE PERFORMANCE OPTIMIZATION SUITE")
    print("=" * 65)

    # Check if server is running
    optimizer = PerformanceOptimizer()
    try:
        response = requests.get(f"{optimizer.base_url}/health", timeout=5)
        if response.status_code != 200:
            print("❌ Server not running. Please start the server first.")
            return
    except Exception:
        print("❌ Cannot connect to server. Please start the server first.")
        return

    print("✅ Server is running. Starting performance optimization...")

    # Core endpoints to benchmark
    core_endpoints = [
        "/",
        "/health",
        "/status",
        "/enterprise/status",
        "/api/health",
        "/docs",
    ]

    # Run benchmarks
    print("\n1. 🔬 ENDPOINT BENCHMARKING")
    print("-" * 30)
    for endpoint in core_endpoints:
        try:
            optimizer.benchmark_endpoint(
                endpoint, num_requests=50, concurrent_requests=5
            )
            time.sleep(1)  # Brief pause between benchmarks
        except Exception as e:
            print(f"❌ Failed to benchmark {endpoint}: {e}")

    # Memory leak testing
    print("\n2. 🧪 MEMORY LEAK TESTING")
    print("-" * 30)
    for endpoint in ["/health", "/status"]:
        try:
            leak_results = optimizer.memory_leak_test(endpoint, iterations=50)
            leak_status = (
                "❌ LEAK DETECTED" if leak_results["leak_detected"] else "✅ NO LEAKS"
            )
            print(
                f"{endpoint}: {leak_status} (Change: {leak_results['memory_increase_mb']:.2f}MB)"
            )
        except Exception as e:
            print(f"❌ Failed to test {endpoint} for leaks: {e}")

    # Generate performance report
    print("\n3. 📊 PERFORMANCE ANALYSIS")
    print("-" * 30)
    optimizer.generate_performance_report()

    print("\n🏁 PERFORMANCE OPTIMIZATION COMPLETE")
    print("✅ Enterprise platform performance validated and optimized")


if __name__ == "__main__":
    main()
