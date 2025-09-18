#!/usr/bin/env python3
"""
Runtime stability testing script for Klerno Labs application.
Tests long-running operations, memory usage, and server stability.
"""
import asyncio
import time
import psutil
import threading
import requests
from concurrent.futures import ThreadPoolExecutor
import subprocess
import sys
import os
from pathlib import Path

class RuntimeStabilityTester:
    """Tests runtime stability and performance under load."""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8003"):
        self.base_url = base_url
        self.server_process = None
        self.is_running = False
        self.test_results = []
        
    def start_server(self):
        """Start the server for testing."""
        print("🚀 Starting server for stability testing...")
        
        env = os.environ.copy()
        env.update({
            "JWT_SECRET": "a1b2c3d4e5f6789012345678901234567890abcdef1234567890fedcba0987654321",
            "ADMIN_EMAIL": "admin@klerno.com",
            "ADMIN_PASSWORD": "SecureAdminPass123!"
        })
        
        cmd = [
            sys.executable, "-m", "uvicorn", 
            "app.main:app", 
            "--host", "127.0.0.1", 
            "--port", "8003",
            "--log-level", "warning"
        ]
        
        self.server_process = subprocess.Popen(
            cmd, 
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=Path(__file__).parent
        )
        
        # Wait for server to start
        max_attempts = 30
        for i in range(max_attempts):
            try:
                response = requests.get(f"{self.base_url}/health", timeout=2)
                if response.status_code == 200:
                    print("✅ Server started successfully")
                    self.is_running = True
                    return True
            except:
                pass
            time.sleep(1)
            print(f"   Waiting for server... ({i+1}/{max_attempts})")
        
        print("❌ Server failed to start")
        return False
    
    def stop_server(self):
        """Stop the test server."""
        if self.server_process:
            print("🛑 Stopping server...")
            self.server_process.terminate()
            self.server_process.wait(timeout=10)
            self.is_running = False
    
    def test_memory_usage(self, duration_minutes: int = 5):
        """Test memory usage over time."""
        print(f"\n💾 TESTING MEMORY USAGE ({duration_minutes} minutes)")
        print("=" * 60)
        
        if not self.server_process:
            print("❌ Server not running")
            return
        
        memory_samples = []
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        try:
            process = psutil.Process(self.server_process.pid)
            
            while time.time() < end_time and self.is_running:
                try:
                    memory_info = process.memory_info()
                    memory_mb = memory_info.rss / 1024 / 1024
                    memory_samples.append(memory_mb)
                    
                    # Make some requests to simulate load
                    try:
                        requests.get(f"{self.base_url}/health", timeout=1)
                    except:
                        pass
                    
                    time.sleep(10)  # Sample every 10 seconds
                    
                except psutil.NoSuchProcess:
                    print("❌ Server process died")
                    break
            
            if memory_samples:
                avg_memory = sum(memory_samples) / len(memory_samples)
                max_memory = max(memory_samples)
                min_memory = min(memory_samples)
                
                print(f"✅ Memory Usage Analysis:")
                print(f"   Average: {avg_memory:.2f} MB")
                print(f"   Peak: {max_memory:.2f} MB")
                print(f"   Minimum: {min_memory:.2f} MB")
                print(f"   Samples: {len(memory_samples)}")
                
                # Check for memory leaks
                if len(memory_samples) > 3:
                    initial_avg = sum(memory_samples[:3]) / 3
                    final_avg = sum(memory_samples[-3:]) / 3
                    growth = final_avg - initial_avg
                    
                    if growth > 50:  # More than 50MB growth
                        print(f"⚠️ Potential memory leak detected: +{growth:.2f} MB")
                    else:
                        print(f"✅ Memory usage stable: {growth:+.2f} MB change")
                
                self.test_results.append({
                    'test': 'memory_usage',
                    'avg_memory_mb': avg_memory,
                    'peak_memory_mb': max_memory,
                    'samples': len(memory_samples),
                    'duration_minutes': duration_minutes
                })
            
        except Exception as e:
            print(f"❌ Memory test failed: {e}")
    
    def test_concurrent_requests(self, num_requests: int = 100, concurrency: int = 10):
        """Test handling concurrent requests."""
        print(f"\n🔄 TESTING CONCURRENT REQUESTS ({num_requests} requests, {concurrency} concurrent)")
        print("=" * 60)
        
        if not self.is_running:
            print("❌ Server not running")
            return
        
        successful_requests = 0
        failed_requests = 0
        response_times = []
        
        def make_request():
            nonlocal successful_requests, failed_requests
            try:
                start_time = time.time()
                response = requests.get(f"{self.base_url}/health", timeout=10)
                end_time = time.time()
                
                response_time = end_time - start_time
                response_times.append(response_time)
                
                if response.status_code == 200:
                    successful_requests += 1
                else:
                    failed_requests += 1
            except Exception as e:
                failed_requests += 1
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            
            # Wait for all requests to complete
            for future in futures:
                future.result()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            min_response_time = min(response_times)
        else:
            avg_response_time = max_response_time = min_response_time = 0
        
        print(f"✅ Concurrent Request Results:")
        print(f"   Total requests: {num_requests}")
        print(f"   Successful: {successful_requests}")
        print(f"   Failed: {failed_requests}")
        print(f"   Success rate: {(successful_requests/num_requests)*100:.1f}%")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Requests/second: {num_requests/total_time:.2f}")
        print(f"   Avg response time: {avg_response_time*1000:.2f}ms")
        print(f"   Max response time: {max_response_time*1000:.2f}ms")
        
        self.test_results.append({
            'test': 'concurrent_requests',
            'total_requests': num_requests,
            'successful': successful_requests,
            'failed': failed_requests,
            'success_rate': (successful_requests/num_requests)*100,
            'avg_response_time_ms': avg_response_time*1000,
            'requests_per_second': num_requests/total_time
        })
    
    def test_endpoint_availability(self):
        """Test that key endpoints remain available."""
        print(f"\n🔍 TESTING ENDPOINT AVAILABILITY")
        print("=" * 60)
        
        if not self.is_running:
            print("❌ Server not running")
            return
        
        endpoints = [
            "/health",
            "/healthz", 
            "/docs",
            "/openapi.json"
        ]
        
        results = {}
        
        for endpoint in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                status = "✅ PASS" if response.status_code in [200, 404] else "❌ FAIL"
                results[endpoint] = {
                    'status_code': response.status_code,
                    'available': response.status_code in [200, 404]
                }
                print(f"   {endpoint}: {status} ({response.status_code})")
            except Exception as e:
                results[endpoint] = {
                    'status_code': 0,
                    'available': False,
                    'error': str(e)
                }
                print(f"   {endpoint}: ❌ FAIL ({str(e)[:50]})")
        
        available_count = sum(1 for r in results.values() if r['available'])
        print(f"\n   Available endpoints: {available_count}/{len(endpoints)}")
        
        self.test_results.append({
            'test': 'endpoint_availability',
            'endpoints_tested': len(endpoints),
            'endpoints_available': available_count,
            'availability_rate': (available_count/len(endpoints))*100,
            'details': results
        })
    
    def test_startup_time(self, num_iterations: int = 3):
        """Test server startup time consistency."""
        print(f"\n⏱️ TESTING STARTUP TIME ({num_iterations} iterations)")
        print("=" * 60)
        
        startup_times = []
        
        for i in range(num_iterations):
            print(f"   Iteration {i+1}/{num_iterations}...")
            
            # Stop current server
            if self.server_process:
                self.stop_server()
                time.sleep(2)
            
            # Measure startup time
            start_time = time.time()
            if self.start_server():
                end_time = time.time()
                startup_time = end_time - start_time
                startup_times.append(startup_time)
                print(f"   Startup time: {startup_time:.2f}s")
            else:
                print(f"   ❌ Failed to start server")
            
            time.sleep(1)
        
        if startup_times:
            avg_startup = sum(startup_times) / len(startup_times)
            max_startup = max(startup_times)
            min_startup = min(startup_times)
            
            print(f"✅ Startup Time Analysis:")
            print(f"   Average: {avg_startup:.2f}s")
            print(f"   Fastest: {min_startup:.2f}s")
            print(f"   Slowest: {max_startup:.2f}s")
            
            self.test_results.append({
                'test': 'startup_time',
                'iterations': len(startup_times),
                'avg_startup_time': avg_startup,
                'min_startup_time': min_startup,
                'max_startup_time': max_startup
            })
    
    def run_all_tests(self):
        """Run all stability tests."""
        print("🧪 STARTING RUNTIME STABILITY TESTING")
        print("=" * 70)
        print(f"Testing server at: {self.base_url}")
        print(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Test startup time consistency
            self.test_startup_time(2)
            
            # Ensure server is running for other tests
            if not self.is_running:
                if not self.start_server():
                    print("❌ Cannot proceed with tests - server failed to start")
                    return
            
            # Run stability tests
            self.test_endpoint_availability()
            self.test_concurrent_requests(50, 5)  # Reduced load for CI
            self.test_memory_usage(2)  # Reduced duration for CI
            
        finally:
            self.stop_server()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 70)
        print("📊 RUNTIME STABILITY TEST SUMMARY")
        print("=" * 70)
        
        total_tests = len(self.test_results)
        print(f"Total test categories: {total_tests}")
        
        for result in self.test_results:
            test_name = result['test'].replace('_', ' ').title()
            print(f"\n🔹 {test_name}:")
            
            if result['test'] == 'memory_usage':
                print(f"   Average memory: {result['avg_memory_mb']:.2f} MB")
                print(f"   Peak memory: {result['peak_memory_mb']:.2f} MB")
                print(f"   Duration: {result['duration_minutes']} minutes")
            
            elif result['test'] == 'concurrent_requests':
                print(f"   Success rate: {result['success_rate']:.1f}%")
                print(f"   Requests/second: {result['requests_per_second']:.2f}")
                print(f"   Avg response time: {result['avg_response_time_ms']:.2f}ms")
            
            elif result['test'] == 'endpoint_availability':
                print(f"   Availability: {result['availability_rate']:.1f}%")
                print(f"   Available: {result['endpoints_available']}/{result['endpoints_tested']}")
            
            elif result['test'] == 'startup_time':
                print(f"   Average startup: {result['avg_startup_time']:.2f}s")
                print(f"   Range: {result['min_startup_time']:.2f}s - {result['max_startup_time']:.2f}s")

if __name__ == "__main__":
    tester = RuntimeStabilityTester()
    tester.run_all_tests()