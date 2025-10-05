#!/usr/bin/env python3
"""Advanced performance profiler for FastAPI application."""

import contextlib
import cProfile
import io
import json
import pstats
import statistics
import threading
import time
from pathlib import Path
from typing import Any

import requests


class FastAPIProfiler:
    """Advanced profiler for FastAPI applications."""

    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        self.base_url = base_url
        self.results = {}

    def profile_endpoint(
        self, endpoint: str, method: str = "GET", runs: int = 100,
    ) -> dict[str, Any]:
        """Profile a specific endpoint with detailed metrics."""
        # Warm up
        for _ in range(5):
            with contextlib.suppress(Exception):
                requests.get(f"{self.base_url}{endpoint}", timeout=5)

        # Profile with cProfile
        profiler = cProfile.Profile()
        response_times = []

        start_total = time.perf_counter()

        for i in range(runs):
            start_request = time.perf_counter()

            if i == 0:  # Profile first request
                profiler.enable()

            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                status_code = response.status_code
                response_size = len(response.content)
            except Exception:
                status_code = 0
                response_size = 0

            if i == 0:
                profiler.disable()

            end_request = time.perf_counter()
            response_times.append((end_request - start_request) * 1000)

        end_total = time.perf_counter()

        # Extract profiling data
        profiling_data = self._extract_profile_data(profiler)

        # Calculate statistics
        if response_times:
            stats = {
                "count": len(response_times),
                "avg_ms": statistics.mean(response_times),
                "median_ms": statistics.median(response_times),
                "min_ms": min(response_times),
                "max_ms": max(response_times),
                "std_dev": (
                    statistics.stdev(response_times) if len(response_times) > 1 else 0
                ),
                "p95_ms": sorted(response_times)[int(len(response_times) * 0.95)],
                "p99_ms": sorted(response_times)[int(len(response_times) * 0.99)],
            }
        else:
            stats = {}

        return {
            "endpoint": endpoint,
            "method": method,
            "runs": runs,
            "total_time_s": end_total - start_total,
            "requests_per_second": (
                runs / (end_total - start_total) if (end_total - start_total) > 0 else 0
            ),
            "response_stats": stats,
            "profiling_data": profiling_data,
            "status_code": status_code,
            "response_size_bytes": response_size,
        }


    def _extract_profile_data(self, profiler: cProfile.Profile) -> dict[str, Any]:
        """Extract meaningful data from cProfile results."""
        # Capture profiler output
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s)
        ps.sort_stats("cumulative")
        ps.print_stats(20)  # Top 20 functions

        profiler_output = s.getvalue()

        # Parse the most time-consuming functions
        lines = profiler_output.split("\n")
        top_functions = []

        for line in lines:
            if "function calls" in line:
                continue
            if line.strip() and not line.startswith(" ") and "/" in line:
                parts = line.split()
                if len(parts) >= 6:
                    try:
                        top_functions.append(
                            {
                                "ncalls": parts[0],
                                "tottime": float(parts[1]),
                                "cumtime": float(parts[3]),
                                "function": parts[5] if len(parts) > 5 else "unknown",
                            },
                        )
                    except (ValueError, IndexError):
                        continue

        return {
            "raw_output": profiler_output,
            "top_functions": top_functions[:10],  # Top 10 most expensive functions
        }

    def benchmark_concurrent_load(
        self, endpoint: str, concurrent_users: int = 10, requests_per_user: int = 50,
    ) -> dict[str, Any]:
        """Benchmark concurrent load on an endpoint."""
        response_times = []
        errors = []
        start_time = time.perf_counter()

        def user_session(user_id: int) -> None:
            """Single user session."""
            session_times = []
            session_errors = []

            for i in range(requests_per_user):
                request_start = time.perf_counter()
                try:
                    response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                    request_end = time.perf_counter()

                    session_times.append((request_end - request_start) * 1000)

                    if response.status_code != 200:
                        session_errors.append(
                            f"User {user_id}, Request {i}: Status {response.status_code}",
                        )

                except Exception as e:
                    request_end = time.perf_counter()
                    session_times.append((request_end - request_start) * 1000)
                    session_errors.append(f"User {user_id}, Request {i}: {e!s}")

            response_times.extend(session_times)
            errors.extend(session_errors)

        # Start concurrent threads
        threads = []
        for user_id in range(concurrent_users):
            thread = threading.Thread(target=user_session, args=(user_id,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        end_time = time.perf_counter()
        total_time = end_time - start_time
        total_requests = concurrent_users * requests_per_user
        successful_requests = total_requests - len(errors)

        # Calculate statistics
        if response_times:
            stats = {
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": len(errors),
                "success_rate": (successful_requests / total_requests) * 100,
                "total_time_s": total_time,
                "requests_per_second": total_requests / total_time,
                "avg_response_time_ms": statistics.mean(response_times),
                "median_response_time_ms": statistics.median(response_times),
                "p95_response_time_ms": sorted(response_times)[
                    int(len(response_times) * 0.95)
                ],
                "p99_response_time_ms": sorted(response_times)[
                    int(len(response_times) * 0.99)
                ],
                "min_response_time_ms": min(response_times),
                "max_response_time_ms": max(response_times),
            }
        else:
            stats = {"error": "No successful requests"}

        return {
            "endpoint": endpoint,
            "concurrent_users": concurrent_users,
            "requests_per_user": requests_per_user,
            "load_test_results": stats,
            "errors": errors[:10],  # First 10 errors
            "error_count": len(errors),
        }

    def memory_profile_endpoint(self, endpoint: str, runs: int = 100) -> dict[str, Any]:
        """Profile memory usage during endpoint execution."""
        try:
            import gc

            import psutil

            process = psutil.Process()

            # Baseline memory
            gc.collect()
            baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

            memory_samples = []

            for i in range(runs):
                pre_request_memory = process.memory_info().rss / 1024 / 1024

                with contextlib.suppress(Exception):
                    requests.get(f"{self.base_url}{endpoint}", timeout=5)

                post_request_memory = process.memory_info().rss / 1024 / 1024
                memory_samples.append(post_request_memory - pre_request_memory)

                if i % 20 == 0:  # Periodic garbage collection
                    gc.collect()

            final_memory = process.memory_info().rss / 1024 / 1024

            return {
                "endpoint": endpoint,
                "runs": runs,
                "baseline_memory_mb": baseline_memory,
                "final_memory_mb": final_memory,
                "memory_growth_mb": final_memory - baseline_memory,
                "avg_memory_per_request_mb": (
                    statistics.mean(memory_samples) if memory_samples else 0
                ),
                "max_memory_spike_mb": max(memory_samples) if memory_samples else 0,
                "memory_samples": memory_samples[:20],  # First 20 samples
            }

        except ImportError:
            return {
                "error": "psutil not available for memory profiling",
                "suggestion": "Install psutil: pip install psutil",
            }

    def comprehensive_analysis(self, endpoints: list[str]) -> dict[str, Any]:
        """Run comprehensive performance analysis on multiple endpoints."""
        results = {
            "analysis_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "base_url": self.base_url,
            "endpoint_profiles": {},
            "load_test_results": {},
            "memory_profiles": {},
            "summary": {},
        }

        total_start = time.perf_counter()

        for endpoint in endpoints:

            # Individual endpoint profiling
            results["endpoint_profiles"][endpoint] = self.profile_endpoint(
                endpoint, runs=50,
            )

            # Load testing
            results["load_test_results"][endpoint] = self.benchmark_concurrent_load(
                endpoint, concurrent_users=5, requests_per_user=20,
            )

            # Memory profiling
            results["memory_profiles"][endpoint] = self.memory_profile_endpoint(
                endpoint, runs=50,
            )

        total_end = time.perf_counter()

        # Generate summary
        summary = self._generate_summary(results)
        results["summary"] = summary
        results["total_analysis_time_s"] = total_end - total_start

        return results

    def _generate_summary(self, results: dict[str, Any]) -> dict[str, Any]:
        """Generate performance summary and recommendations."""
        endpoint_performances = []
        load_test_performances = []

        for endpoint, profile in results["endpoint_profiles"].items():
            if profile.get("response_stats"):
                endpoint_performances.append(
                    {
                        "endpoint": endpoint,
                        "avg_ms": profile["response_stats"]["avg_ms"],
                        "p95_ms": profile["response_stats"]["p95_ms"],
                        "rps": profile.get("requests_per_second", 0),
                    },
                )

        for endpoint, load_test in results["load_test_results"].items():
            if (
                "load_test_results" in load_test
                and "requests_per_second" in load_test["load_test_results"]
            ):
                load_test_performances.append(
                    {
                        "endpoint": endpoint,
                        "rps": load_test["load_test_results"]["requests_per_second"],
                        "success_rate": load_test["load_test_results"].get(
                            "success_rate", 0,
                        ),
                    },
                )

        # Find best and worst performing endpoints
        best_endpoint = (
            min(endpoint_performances, key=lambda x: x["avg_ms"])
            if endpoint_performances
            else None
        )
        worst_endpoint = (
            max(endpoint_performances, key=lambda x: x["avg_ms"])
            if endpoint_performances
            else None
        )

        # Calculate overall performance score
        avg_response_times = [ep["avg_ms"] for ep in endpoint_performances]
        overall_avg_ms = (
            statistics.mean(avg_response_times) if avg_response_times else 0
        )

        performance_tier = (
            "EXCELLENT"
            if overall_avg_ms < 10
            else (
                "GOOD"
                if overall_avg_ms < 50
                else "ACCEPTABLE"
                if overall_avg_ms < 100
                else "NEEDS_IMPROVEMENT"
            )
        )

        return {
            "overall_performance_tier": performance_tier,
            "average_response_time_ms": overall_avg_ms,
            "best_performing_endpoint": best_endpoint,
            "worst_performing_endpoint": worst_endpoint,
            "total_endpoints_analyzed": len(endpoint_performances),
            "recommendations": self._generate_recommendations(results),
        }

    def _generate_recommendations(self, results: dict[str, Any]) -> list[str]:
        """Generate performance improvement recommendations."""
        recommendations = []

        # Analyze response times
        slow_endpoints = []
        for endpoint, profile in results["endpoint_profiles"].items():
            if profile.get("response_stats"):
                avg_ms = profile["response_stats"]["avg_ms"]
                if avg_ms > 50:
                    slow_endpoints.append(f"{endpoint} ({avg_ms:.2f}ms)")

        if slow_endpoints:
            recommendations.append(
                f"Optimize slow endpoints: {', '.join(slow_endpoints)}",
            )
        else:
            recommendations.append(
                "✅ All endpoints have excellent response times (<50ms)",
            )

        # Analyze load test results
        low_throughput_endpoints = []
        for endpoint, load_test in results["load_test_results"].items():
            if "load_test_results" in load_test:
                rps = load_test["load_test_results"].get("requests_per_second", 0)
                if rps < 100:
                    low_throughput_endpoints.append(f"{endpoint} ({rps:.1f} RPS)")

        if low_throughput_endpoints:
            recommendations.append(
                f"Improve throughput for: {', '.join(low_throughput_endpoints)}",
            )
        else:
            recommendations.append("✅ All endpoints have good throughput (>100 RPS)")

        # Memory recommendations
        high_memory_endpoints = []
        for endpoint, memory_profile in results["memory_profiles"].items():
            if "memory_growth_mb" in memory_profile:
                growth = memory_profile["memory_growth_mb"]
                if growth > 10:  # More than 10MB growth
                    high_memory_endpoints.append(f"{endpoint} (+{growth:.2f}MB)")

        if high_memory_endpoints:
            recommendations.append(
                f"Investigate memory usage in: {', '.join(high_memory_endpoints)}",
            )
        else:
            recommendations.append("✅ Memory usage is well controlled")

        return recommendations


def main() -> None:
    """Run comprehensive performance profiling."""
    # Test if server is running
    try:
        requests.get("http://localhost:8000/health", timeout=5)
    except Exception:
        return

    profiler = FastAPIProfiler()

    # Define endpoints to test
    endpoints_to_test = [
        "/health",
        "/healthz",
        "/status",
        "/",
    ]

    # Run comprehensive analysis
    results = profiler.comprehensive_analysis(endpoints_to_test)

    # Save results
    output_file = "advanced_performance_profile.json"
    with Path(output_file).open("w") as f:
        json.dump(results, f, indent=2)

    # Print summary

    summary = results["summary"]

    if summary["best_performing_endpoint"]:
        summary["best_performing_endpoint"]

    if summary["worst_performing_endpoint"]:
        summary["worst_performing_endpoint"]

    for _rec in summary["recommendations"]:
        pass



if __name__ == "__main__":
    main()
