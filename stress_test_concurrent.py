#!/usr/bin/env python3
"""
Custom Concurrent Load Test
Tests the live server with multiple concurrent requests to verify stability under load
"""

import asyncio
import statistics
import time
from concurrent.futures import ThreadPoolExecutor

import aiohttp
import requests

BASE_URL = "http://127.0.0.1:8002"

# Test routes to stress test
TEST_ROUTES = [
    "/",
    "/health",
    "/status",
    "/dashboard",
    "/admin",
    "/docs",
    "/admin/api/stats",
    "/premium/advanced-analytics",
    "/api/health",
    "/enterprise/status",
]


def sync_load_test(route, num_requests=20):
    """Synchronous load test using requests library"""
    print(f"Testing {route} with {num_requests} requests...")

    times = []
    success_count = 0
    error_count = 0

    for i in range(num_requests):
        start_time = time.time()
        try:
            response = requests.get(f"{BASE_URL}{route}", timeout=10)
            end_time = time.time()

            if response.status_code == 200:
                success_count += 1
            else:
                error_count += 1
                print(f"  Request {i+1}: Status {response.status_code}")

            times.append(end_time - start_time)

        except Exception as e:
            error_count += 1
            print(f"  Request {i+1}: Error - {e}")
            times.append(10.0)  # Max timeout

    if times:
        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        median_time = statistics.median(times)
    else:
        avg_time = min_time = max_time = median_time = 0

    return {
        "route": route,
        "total_requests": num_requests,
        "success_count": success_count,
        "error_count": error_count,
        "success_rate": success_count / num_requests if num_requests > 0 else 0,
        "avg_time": avg_time,
        "min_time": min_time,
        "max_time": max_time,
        "median_time": median_time,
    }


async def async_load_test(route, num_requests=20):
    """Asynchronous load test using aiohttp"""
    print(f"Async testing {route} with {num_requests} requests...")

    times = []
    success_count = 0
    error_count = 0

    async with aiohttp.ClientSession() as session:

        async def make_request(session, url):
            start_time = time.time()
            try:
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    end_time = time.time()
                    return response.status, end_time - start_time
            except Exception as e:
                end_time = time.time()
                return 0, end_time - start_time

        # Create all request tasks
        tasks = [
            make_request(session, f"{BASE_URL}{route}") for _ in range(num_requests)
        ]

        # Execute all requests concurrently
        results = await asyncio.gather(*tasks)

        for status, duration in results:
            times.append(duration)
            if status == 200:
                success_count += 1
            else:
                error_count += 1

    if times:
        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        median_time = statistics.median(times)
    else:
        avg_time = min_time = max_time = median_time = 0

    return {
        "route": route,
        "total_requests": num_requests,
        "success_count": success_count,
        "error_count": error_count,
        "success_rate": success_count / num_requests if num_requests > 0 else 0,
        "avg_time": avg_time,
        "min_time": min_time,
        "max_time": max_time,
        "median_time": median_time,
    }


def run_concurrent_stress_test():
    """Run comprehensive concurrent stress test"""
    print("=" * 80)
    print("KLERNO LABS CONCURRENT STRESS TEST")
    print("=" * 80)

    # Test server availability first
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ Server not responding properly. Status: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return

    print("✅ Server is running and responsive")
    print()

    # 1. Sequential load test
    print("1. SEQUENTIAL LOAD TEST")
    print("-" * 40)

    sequential_results = []
    for route in TEST_ROUTES:
        result = sync_load_test(route, 10)
        sequential_results.append(result)
        print(
            f"  {route}: {result['success_count']}/{result['total_requests']} success, "
            f"avg: {result['avg_time']:.3f}s"
        )

    print()

    # 2. Concurrent load test using asyncio
    print("2. CONCURRENT LOAD TEST (ASYNCIO)")
    print("-" * 40)

    async def run_async_tests():
        tasks = [async_load_test(route, 15) for route in TEST_ROUTES]
        return await asyncio.gather(*tasks)

    concurrent_results = asyncio.run(run_async_tests())

    for result in concurrent_results:
        print(
            f"  {result['route']}: {result['success_count']}/{result['total_requests']} success, "
            f"avg: {result['avg_time']:.3f}s"
        )

    print()

    # 3. High concurrency test on single endpoint
    print("3. HIGH CONCURRENCY TEST (100 requests to /health)")
    print("-" * 50)

    health_stress = sync_load_test("/health", 100)
    print(
        f"  Results: {health_stress['success_count']}/{health_stress['total_requests']} success"
    )
    print(f"  Success rate: {health_stress['success_rate']*100:.1f}%")
    print(f"  Average time: {health_stress['avg_time']:.3f}s")
    print(
        f"  Min/Max time: {health_stress['min_time']:.3f}s / {health_stress['max_time']:.3f}s"
    )

    print()

    # 4. Mixed concurrent requests to different endpoints
    print("4. MIXED ENDPOINT CONCURRENT TEST")
    print("-" * 40)

    def mixed_endpoint_test():
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for route in TEST_ROUTES:
                future = executor.submit(sync_load_test, route, 5)
                futures.append(future)

            mixed_results = []
            for future in futures:
                mixed_results.append(future.result())

            return mixed_results

    mixed_results = mixed_endpoint_test()

    total_requests = sum(r["total_requests"] for r in mixed_results)
    total_success = sum(r["success_count"] for r in mixed_results)
    overall_success_rate = total_success / total_requests if total_requests > 0 else 0

    print(f"  Overall: {total_success}/{total_requests} success")
    print(f"  Overall success rate: {overall_success_rate*100:.1f}%")

    print()

    # 5. Summary and analysis
    print("5. STRESS TEST SUMMARY")
    print("-" * 30)

    all_success_rates = []
    all_success_rates.extend(r["success_rate"] for r in sequential_results)
    all_success_rates.extend(r["success_rate"] for r in concurrent_results)
    all_success_rates.append(health_stress["success_rate"])
    all_success_rates.append(overall_success_rate)

    avg_success_rate = statistics.mean(all_success_rates)
    min_success_rate = min(all_success_rates)

    print(f"  Average success rate across all tests: {avg_success_rate*100:.1f}%")
    print(f"  Minimum success rate: {min_success_rate*100:.1f}%")

    if min_success_rate >= 0.95:
        print("  ✅ EXCELLENT: All tests achieved >95% success rate")
    elif min_success_rate >= 0.90:
        print("  ✅ GOOD: All tests achieved >90% success rate")
    elif min_success_rate >= 0.80:
        print("  ⚠️  ACCEPTABLE: Some tests had 80-90% success rate")
    else:
        print("  ❌ POOR: Some tests had <80% success rate")

    # Check response times
    all_avg_times = []
    all_avg_times.extend(r["avg_time"] for r in sequential_results)
    all_avg_times.extend(r["avg_time"] for r in concurrent_results)
    all_avg_times.append(health_stress["avg_time"])

    avg_response_time = statistics.mean(all_avg_times)
    max_response_time = max(all_avg_times)

    print(f"  Average response time: {avg_response_time:.3f}s")
    print(f"  Maximum response time: {max_response_time:.3f}s")

    if max_response_time <= 1.0:
        print("  ✅ EXCELLENT: All responses under 1 second")
    elif max_response_time <= 2.0:
        print("  ✅ GOOD: All responses under 2 seconds")
    elif max_response_time <= 5.0:
        print("  ⚠️  ACCEPTABLE: Some responses took 2-5 seconds")
    else:
        print("  ❌ SLOW: Some responses took over 5 seconds")


if __name__ == "__main__":
    run_concurrent_stress_test()
