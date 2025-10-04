#!/usr/bin/env python3
"""KLERNO LABS ENTERPRISE PLATFORM - QUICK API LOAD TEST
======================================================

Simplified but comprehensive API load testing with stability focus.
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp


class QuickLoadTester:
    """Simplified load tester for reliable testing"""

    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.results = []

        # Test endpoints
        self.endpoints = [
            "/health",
            "/status",
            "/docs",
            "/enterprise/status",
            "/enterprise/health",
        ]

    async def test_endpoint(
        self, session: aiohttp.ClientSession, endpoint: str,
    ) -> dict[str, Any]:
        """Test a single endpoint and return results"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()

        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with session.get(url, timeout=timeout) as response:
                await response.read()
                response_time = time.time() - start_time

                return {
                    "endpoint": endpoint,
                    "status_code": response.status,
                    "response_time": response_time,
                    "success": response.status == 200,
                    "timestamp": datetime.now().isoformat(),
                }
        except Exception as e:
            return {
                "endpoint": endpoint,
                "status_code": 0,
                "response_time": time.time() - start_time,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def run_single_user_test(
        self,
        session: aiohttp.ClientSession,
        user_id: int,
        requests_per_endpoint: int = 5,
    ) -> list[dict[str, Any]]:
        """Run test for a single simulated user"""
        user_results = []

        for endpoint in self.endpoints:
            for _ in range(requests_per_endpoint):
                result = await self.test_endpoint(session, endpoint)
                result["user_id"] = user_id
                user_results.append(result)

                # Small delay between requests
                await asyncio.sleep(0.1)

        return user_results

    async def run_load_test(
        self, concurrent_users: int = 10, requests_per_endpoint: int = 3,
    ) -> dict[str, Any]:
        """Run load test with specified parameters"""
        print(
            f"🚀 Starting load test with {concurrent_users} users, {requests_per_endpoint} requests per endpoint",
        )

        all_results = []
        start_time = datetime.now()

        # Create session with connection pooling
        connector = aiohttp.TCPConnector(limit=50, limit_per_host=25)

        async with aiohttp.ClientSession(connector=connector) as session:
            # Create tasks for concurrent users
            tasks = []
            for user_id in range(concurrent_users):
                task = asyncio.create_task(
                    self.run_single_user_test(session, user_id, requests_per_endpoint),
                )
                tasks.append(task)

            # Wait for all users to complete
            user_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Flatten results
            for results in user_results:
                if isinstance(results, list):
                    all_results.extend(results)

        end_time = datetime.now()

        return self.analyze_results(all_results, start_time, end_time, concurrent_users)

    def analyze_results(
        self,
        results: list[dict[str, Any]],
        start_time: datetime,
        end_time: datetime,
        users: int,
    ) -> dict[str, Any]:
        """Analyze load test results"""
        if not results:
            return {"error": "No results to analyze"}

        # Basic stats
        total_requests = len(results)
        successful_requests = sum(1 for r in results if r.get("success", False))
        failed_requests = total_requests - successful_requests

        # Response times
        response_times = [r["response_time"] for r in results if "response_time" in r]
        avg_response_time = (
            sum(response_times) / len(response_times) if response_times else 0
        )
        max_response_time = max(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0

        # Throughput
        duration = (end_time - start_time).total_seconds()
        requests_per_second = total_requests / duration if duration > 0 else 0

        # Endpoint analysis
        endpoint_stats = {}
        for result in results:
            endpoint = result["endpoint"]
            if endpoint not in endpoint_stats:
                endpoint_stats[endpoint] = {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "response_times": [],
                }

            endpoint_stats[endpoint]["total"] += 1
            if result.get("success", False):
                endpoint_stats[endpoint]["successful"] += 1
            else:
                endpoint_stats[endpoint]["failed"] += 1

            if "response_time" in result:
                endpoint_stats[endpoint]["response_times"].append(
                    result["response_time"],
                )

        # Calculate endpoint averages
        for _endpoint, stats in endpoint_stats.items():
            if stats["response_times"]:
                stats["avg_response_time"] = sum(stats["response_times"]) / len(
                    stats["response_times"],
                )
                stats["max_response_time"] = max(stats["response_times"])
            stats["success_rate"] = (
                (stats["successful"] / stats["total"]) * 100
                if stats["total"] > 0
                else 0
            )
            del stats["response_times"]  # Remove raw data for cleaner output

        return {
            "test_summary": {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "concurrent_users": users,
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "success_rate": (successful_requests / total_requests) * 100,
                "requests_per_second": requests_per_second,
            },
            "performance_metrics": {
                "average_response_time": avg_response_time,
                "min_response_time": min_response_time,
                "max_response_time": max_response_time,
            },
            "endpoint_analysis": endpoint_stats,
            "raw_results": results,
        }

    def generate_report(self, analysis: dict[str, Any]):
        """Generate a comprehensive test report"""
        if "error" in analysis:
            print(f"❌ {analysis['error']}")
            return

        summary = analysis["test_summary"]
        metrics = analysis["performance_metrics"]
        endpoints = analysis["endpoint_analysis"]

        print("\n📊 KLERNO LABS QUICK API LOAD TEST REPORT")
        print("=" * 55)

        # Test Summary
        print("\n⚙️  TEST SUMMARY")
        print("-" * 25)
        print(f"Duration: {summary['duration_seconds']:.1f} seconds")
        print(f"Concurrent Users: {summary['concurrent_users']}")
        print(f"Total Requests: {summary['total_requests']:,}")
        print(f"Successful: {summary['successful_requests']:,}")
        print(f"Failed: {summary['failed_requests']:,}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print(f"Throughput: {summary['requests_per_second']:.1f} requests/second")

        # Performance Metrics
        print("\n⚡ PERFORMANCE METRICS")
        print("-" * 25)
        print(f"Average Response Time: {metrics['average_response_time']:.3f}s")
        print(f"Minimum Response Time: {metrics['min_response_time']:.3f}s")
        print(f"Maximum Response Time: {metrics['max_response_time']:.3f}s")

        # Endpoint Analysis
        print("\n🎯 ENDPOINT PERFORMANCE")
        print("-" * 35)
        for endpoint, stats in endpoints.items():
            status_icon = (
                "✅"
                if stats["success_rate"] >= 95
                else "⚠️" if stats["success_rate"] >= 90 else "❌"
            )
            print(f"{status_icon} {endpoint}")
            print(
                f"   Requests: {stats['total']} | Success Rate: {stats['success_rate']:.1f}%",
            )
            if "avg_response_time" in stats:
                print(
                    f"   Avg Time: {stats['avg_response_time']:.3f}s | Max Time: {stats['max_response_time']:.3f}s",
                )

        # Overall Assessment
        print("\n🎯 PERFORMANCE ASSESSMENT")
        print("-" * 30)

        if summary["success_rate"] >= 99:
            print("✅ Excellent reliability (≥99% success rate)")
        elif summary["success_rate"] >= 95:
            print("⚠️  Good reliability (≥95% success rate)")
        else:
            print("❌ Poor reliability (<95% success rate)")

        if metrics["average_response_time"] < 0.1:
            print("✅ Excellent response time (<100ms)")
        elif metrics["average_response_time"] < 0.5:
            print("⚠️  Good response time (<500ms)")
        else:
            print("❌ Slow response time (≥500ms)")

        if summary["requests_per_second"] > 50:
            print("✅ Good throughput (>50 RPS)")
        elif summary["requests_per_second"] > 20:
            print("⚠️  Moderate throughput (>20 RPS)")
        else:
            print("❌ Low throughput (≤20 RPS)")


async def main():
    """Run comprehensive quick load tests"""
    print("🚀 KLERNO LABS QUICK API LOAD TESTING")
    print("=" * 45)

    tester = QuickLoadTester()

    # Test scenarios
    scenarios = [
        {"name": "Light Load", "users": 5, "requests": 3},
        {"name": "Moderate Load", "users": 15, "requests": 4},
        {"name": "Heavy Load", "users": 30, "requests": 5},
    ]

    all_results = []

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n🎯 Test {i}/3: {scenario['name']}")
        print(
            f"   Users: {scenario['users']}, Requests per endpoint: {scenario['requests']}",
        )
        print("-" * 40)

        try:
            # Run test
            analysis = await tester.run_load_test(
                concurrent_users=scenario["users"],
                requests_per_endpoint=scenario["requests"],
            )

            # Generate report
            tester.generate_report(analysis)

            # Export results
            filename = (
                f"quick_load_test_{i}_{scenario['name'].lower().replace(' ', '_')}.json"
            )
            with Path(filename).open("w") as f:
                json.dump(analysis, f, indent=2)

            all_results.append(analysis)

        except Exception as e:
            print(f"❌ Test {i} failed: {e}")

        # Brief pause between tests
        if i < len(scenarios):
            print("\n⏳ Waiting 5 seconds before next test...")
            await asyncio.sleep(5)

    # Summary
    print("\n📋 COMPREHENSIVE TEST SUMMARY")
    print("=" * 40)

    for i, (scenario, analysis) in enumerate(zip(scenarios, all_results, strict=False), 1):
        if "test_summary" in analysis:
            summary = analysis["test_summary"]
            print(f"\n{i}. {scenario['name']}:")
            print(f"   Success Rate: {summary['success_rate']:.1f}%")
            print(
                f"   Avg Response Time: {analysis['performance_metrics']['average_response_time']:.3f}s",
            )
            print(f"   Throughput: {summary['requests_per_second']:.1f} RPS")

    print("\n✅ Quick load testing completed!")


if __name__ == "__main__":
    asyncio.run(main())

