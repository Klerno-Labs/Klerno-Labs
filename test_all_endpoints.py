#!/usr/bin/env python3
"""
Comprehensive API endpoint testing script for Klerno Labs application.
Tests all major endpoints systematically.
"""
import requests
import json
import time
from typing import Dict, List, Any
import sys

class APITester:
    """Comprehensive API endpoint tester."""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8002"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results: List[Dict] = []
        self.token = None
        
    def log_result(self, endpoint: str, method: str, status_code: int, 
                   response_time: float, success: bool, error: str = None):
        """Log test result."""
        result = {
            'endpoint': endpoint,
            'method': method,
            'status_code': status_code,
            'response_time_ms': round(response_time * 1000, 2),
            'success': success,
            'error': error
        }
        self.results.append(result)
        
        status_emoji = "✅" if success else "❌"
        print(f"{status_emoji} {method} {endpoint} - {status_code} ({result['response_time_ms']}ms)")
        if error:
            print(f"   Error: {error}")
    
    def test_endpoint(self, endpoint: str, method: str = "GET", 
                     data: Dict = None, headers: Dict = None, 
                     expected_codes: List[int] = None) -> bool:
        """Test a single endpoint."""
        if expected_codes is None:
            expected_codes = [200, 201, 202, 204]
            
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            if method == "GET":
                response = self.session.get(url, headers=headers, timeout=10)
            elif method == "POST":
                response = self.session.post(url, json=data, headers=headers, timeout=10)
            elif method == "PUT":
                response = self.session.put(url, json=data, headers=headers, timeout=10)
            elif method == "DELETE":
                response = self.session.delete(url, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            response_time = time.time() - start_time
            success = response.status_code in expected_codes
            error = None if success else f"Unexpected status code: {response.status_code}"
            
            # Try to get response text for debugging
            try:
                if not success and len(response.text) < 200:
                    error += f" - {response.text}"
            except:
                pass
                
        except requests.exceptions.RequestException as e:
            response_time = time.time() - start_time
            success = False
            error = str(e)
            response = None
            
        status_code = response.status_code if response else 0
        self.log_result(endpoint, method, status_code, response_time, success, error)
        return success
    
    def test_health_endpoints(self):
        """Test health check endpoints."""
        print("\n🏥 TESTING HEALTH ENDPOINTS")
        print("=" * 50)
        
        health_endpoints = [
            "/health",
            "/healthz", 
            "/api/health-check",
            "/enterprise/health"
        ]
        
        for endpoint in health_endpoints:
            self.test_endpoint(endpoint)
    
    def test_authentication_endpoints(self):
        """Test authentication related endpoints."""
        print("\n🔐 TESTING AUTHENTICATION ENDPOINTS")
        print("=" * 50)
        
        # Test auth endpoints (expecting 401/422 for missing data)
        auth_endpoints = [
            ("/auth/login", "POST", [401, 422]),
            ("/auth/logout", "POST", [200, 401]),
            ("/auth/register", "POST", [422]),  # Missing required fields
            ("/auth/refresh", "POST", [401, 422]),
            ("/auth/me", "GET", [401]),  # No token provided
        ]
        
        for endpoint, method, expected in auth_endpoints:
            self.test_endpoint(endpoint, method, expected_codes=expected)
    
    def test_admin_endpoints(self):
        """Test admin endpoints."""
        print("\n👑 TESTING ADMIN ENDPOINTS")
        print("=" * 50)
        
        admin_endpoints = [
            ("/admin", "GET", [200, 401, 403]),  # May redirect or require auth
            ("/admin/users", "GET", [401, 403]),  # Requires admin access
            ("/admin/settings", "GET", [401, 403]),
            ("/admin/logs", "GET", [401, 403]),
            ("/admin/stats", "GET", [401, 403]),
        ]
        
        for endpoint, method, expected in admin_endpoints:
            self.test_endpoint(endpoint, method, expected_codes=expected)
    
    def test_api_endpoints(self):
        """Test general API endpoints."""
        print("\n🔌 TESTING GENERAL API ENDPOINTS")
        print("=" * 50)
        
        api_endpoints = [
            ("/api", "GET"),
            ("/api/status", "GET"),
            ("/api/version", "GET"),
            ("/docs", "GET"),  # OpenAPI docs
            ("/redoc", "GET"), # ReDoc
            ("/openapi.json", "GET"),  # OpenAPI spec
        ]
        
        for endpoint_data in api_endpoints:
            if len(endpoint_data) == 2:
                endpoint, method = endpoint_data
                expected = [200, 404]  # Some may not exist
            else:
                endpoint, method, expected = endpoint_data
            self.test_endpoint(endpoint, method, expected_codes=expected)
    
    def test_enterprise_endpoints(self):
        """Test enterprise feature endpoints."""
        print("\n🏢 TESTING ENTERPRISE ENDPOINTS")
        print("=" * 50)
        
        enterprise_endpoints = [
            ("/enterprise/monitoring", "GET", [200, 401, 403]),
            ("/enterprise/analytics", "GET", [200, 401, 403]),
            ("/enterprise/compliance", "GET", [200, 401, 403]),
            ("/enterprise/security", "GET", [200, 401, 403]),
            ("/enterprise/reporting", "GET", [200, 401, 403]),
            ("/enterprise/iso20022", "GET", [200, 401, 403]),
        ]
        
        for endpoint, method, expected in enterprise_endpoints:
            self.test_endpoint(endpoint, method, expected_codes=expected)
    
    def test_blockchain_endpoints(self):
        """Test blockchain and cryptocurrency endpoints."""
        print("\n₿ TESTING BLOCKCHAIN ENDPOINTS")
        print("=" * 50)
        
        crypto_endpoints = [
            ("/api/crypto/balance", "GET", [401, 403, 422]),
            ("/api/crypto/transaction", "POST", [401, 403, 422]),
            ("/api/xrp/balance", "GET", [401, 403, 422]),
            ("/api/xrp/payment", "POST", [401, 403, 422]),
            ("/api/blockchain/status", "GET", [200, 401]),
        ]
        
        for endpoint, method, expected in crypto_endpoints:
            self.test_endpoint(endpoint, method, expected_codes=expected)
    
    def test_payment_endpoints(self):
        """Test payment and paywall endpoints."""
        print("\n💳 TESTING PAYMENT ENDPOINTS")
        print("=" * 50)
        
        payment_endpoints = [
            ("/api/payments/create", "POST", [401, 403, 422]),
            ("/api/payments/status", "GET", [401, 403, 422]),
            ("/api/subscription/status", "GET", [401, 403]),
            ("/api/subscription/upgrade", "POST", [401, 403, 422]),
            ("/paywall", "GET", [200, 401]),
        ]
        
        for endpoint, method, expected in payment_endpoints:
            self.test_endpoint(endpoint, method, expected_codes=expected)
    
    def test_compliance_endpoints(self):
        """Test compliance and reporting endpoints."""
        print("\n📋 TESTING COMPLIANCE ENDPOINTS")
        print("=" * 50)
        
        compliance_endpoints = [
            ("/api/compliance/check", "POST", [401, 403, 422]),
            ("/api/compliance/report", "GET", [401, 403]),
            ("/api/compliance/audit", "GET", [401, 403]),
            ("/api/iso20022/validate", "POST", [401, 403, 422]),
            ("/api/iso20022/process", "POST", [401, 403, 422]),
        ]
        
        for endpoint, method, expected in compliance_endpoints:
            self.test_endpoint(endpoint, method, expected_codes=expected)
    
    def run_all_tests(self):
        """Run all endpoint tests."""
        print("🚀 STARTING COMPREHENSIVE API ENDPOINT TESTING")
        print("=" * 60)
        print(f"Testing server at: {self.base_url}")
        print(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Wait for server to be ready
        print("\n⏳ Waiting for server to be ready...")
        for i in range(10):
            try:
                response = requests.get(f"{self.base_url}/health", timeout=2)
                if response.status_code == 200:
                    print("✅ Server is ready!")
                    break
            except:
                pass
            time.sleep(1)
            print(f"   Attempt {i+1}/10...")
        
        # Run all test suites
        test_suites = [
            self.test_health_endpoints,
            self.test_api_endpoints,
            self.test_authentication_endpoints,
            self.test_admin_endpoints,
            self.test_enterprise_endpoints,
            self.test_blockchain_endpoints,
            self.test_payment_endpoints,
            self.test_compliance_endpoints,
        ]
        
        for test_suite in test_suites:
            try:
                test_suite()
            except Exception as e:
                print(f"❌ Error in test suite {test_suite.__name__}: {e}")
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r['success'])
        failed_tests = total_tests - successful_tests
        
        print(f"Total endpoints tested: {total_tests}")
        print(f"✅ Successful: {successful_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success rate: {(successful_tests/total_tests*100):.1f}%" if total_tests > 0 else "0.0%")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED ENDPOINTS ({failed_tests}):")
            for result in self.results:
                if not result['success']:
                    print(f"   {result['method']} {result['endpoint']} - {result['status_code']}")
                    if result['error']:
                        print(f"      {result['error']}")
        
        # Performance stats
        response_times = [r['response_time_ms'] for r in self.results if r['success']]
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            print(f"\n⚡ PERFORMANCE STATS:")
            print(f"   Average response time: {avg_time:.2f}ms")
            print(f"   Fastest response: {min_time:.2f}ms")
            print(f"   Slowest response: {max_time:.2f}ms")

if __name__ == "__main__":
    tester = APITester()
    tester.run_all_tests()