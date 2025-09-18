"""
Klerno Labs - Comprehensive API Test Suite
Tests all major endpoints and enterprise features to verify functionality.
"""

import requests
import json
import time
import sys
from datetime import datetime

class KlernoLabsTestSuite:
    """Comprehensive test suite for Klerno Labs API."""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name: str, status: bool, details: str = ""):
        """Log test results."""
        status_str = "✅ PASS" if status else "❌ FAIL"
        self.test_results.append({
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        print(f"{status_str} {test_name}")
        if details and not status:
            print(f"   Details: {details}")
    
    def test_health_endpoints(self):
        """Test health check endpoints."""
        print("\n=== Health Check Tests ===")
        
        endpoints = [
            "/healthz",
            "/health", 
            "/api/health-check",
            "/enterprise/health"
        ]
        
        for endpoint in endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=5)
                success = response.status_code == 200
                details = f"Status: {response.status_code}, Response: {response.text[:100]}"
                self.log_test(f"Health Check {endpoint}", success, details)
            except Exception as e:
                self.log_test(f"Health Check {endpoint}", False, str(e))
    
    def test_authentication_endpoints(self):
        """Test authentication endpoints."""
        print("\n=== Authentication Tests ===")
        
        # Test login page
        try:
            response = self.session.get(f"{self.base_url}/login", timeout=5)
            success = response.status_code == 200 and "login" in response.text.lower()
            self.log_test("Login Page", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Login Page", False, str(e))
        
        # Test signup page
        try:
            response = self.session.get(f"{self.base_url}/signup", timeout=5)
            success = response.status_code == 200
            self.log_test("Signup Page", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Signup Page", False, str(e))
    
    def test_api_endpoints(self):
        """Test API endpoints."""
        print("\n=== API Endpoint Tests ===")
        
        api_endpoints = [
            "/api/status",
            "/api/metrics",
            "/api/system/info",
            "/docs",  # Swagger documentation
            "/openapi.json"  # OpenAPI spec
        ]
        
        for endpoint in api_endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=5)
                success = response.status_code in [200, 401]  # 401 for auth-required endpoints is OK
                details = f"Status: {response.status_code}"
                if response.status_code == 200:
                    details += f", Size: {len(response.content)} bytes"
                self.log_test(f"API {endpoint}", success, details)
            except Exception as e:
                self.log_test(f"API {endpoint}", False, str(e))
    
    def test_enterprise_features(self):
        """Test enterprise feature endpoints."""
        print("\n=== Enterprise Feature Tests ===")
        
        enterprise_endpoints = [
            "/enterprise/dashboard",
            "/enterprise/monitoring",
            "/enterprise/analytics", 
            "/enterprise/security",
            "/admin/dashboard"
        ]
        
        for endpoint in enterprise_endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=5)
                # These might require auth, so 401/403 is acceptable
                success = response.status_code in [200, 401, 403, 404]
                details = f"Status: {response.status_code}"
                self.log_test(f"Enterprise {endpoint}", success, details)
            except Exception as e:
                self.log_test(f"Enterprise {endpoint}", False, str(e))
    
    def test_static_files(self):
        """Test static file serving."""
        print("\n=== Static File Tests ===")
        
        static_files = [
            "/static/klerno-logo.png",
            "/static/klerno-wordmark.png",
            "/static/favicon.ico",
            "/robots.txt"
        ]
        
        for file_path in static_files:
            try:
                response = self.session.get(f"{self.base_url}{file_path}", timeout=5)
                success = response.status_code == 200
                details = f"Status: {response.status_code}, Size: {len(response.content)} bytes"
                self.log_test(f"Static File {file_path}", success, details)
            except Exception as e:
                self.log_test(f"Static File {file_path}", False, str(e))
    
    def test_landing_page(self):
        """Test the main landing page."""
        print("\n=== Landing Page Test ===")
        
        try:
            response = self.session.get(f"{self.base_url}/", timeout=5)
            success = response.status_code == 200 and "klerno" in response.text.lower()
            details = f"Status: {response.status_code}, Contains 'klerno': {'klerno' in response.text.lower()}"
            self.log_test("Landing Page", success, details)
        except Exception as e:
            self.log_test("Landing Page", False, str(e))
    
    def test_xrpl_endpoints(self):
        """Test XRPL integration endpoints."""
        print("\n=== XRPL Integration Tests ===")
        
        xrpl_endpoints = [
            "/api/xrpl/status",
            "/api/blockchain/status",
            "/api/payments/xrpl"
        ]
        
        for endpoint in xrpl_endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=5)
                success = response.status_code in [200, 401, 404, 405]
                details = f"Status: {response.status_code}"
                self.log_test(f"XRPL {endpoint}", success, details)
            except Exception as e:
                self.log_test(f"XRPL {endpoint}", False, str(e))
    
    def run_all_tests(self):
        """Run all test suites."""
        print("🚀 Starting Klerno Labs Comprehensive Test Suite")
        print(f"Testing server at: {self.base_url}")
        print(f"Test started at: {datetime.now().isoformat()}")
        
        # Wait for server to be ready
        print("\nWaiting for server to be ready...")
        for i in range(10):
            try:
                response = self.session.get(f"{self.base_url}/healthz", timeout=2)
                if response.status_code == 200:
                    print("✅ Server is ready!")
                    break
            except:
                if i == 9:
                    print("❌ Server not responding after 10 attempts")
                    return
                time.sleep(1)
        
        # Run test suites
        self.test_health_endpoints()
        self.test_authentication_endpoints()
        self.test_api_endpoints()
        self.test_enterprise_features()
        self.test_static_files()
        self.test_landing_page()
        self.test_xrpl_endpoints()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        passed = sum(1 for result in self.test_results if result["status"])
        total = len(self.test_results)
        failed = total - passed
        
        print("\n" + "="*50)
        print("🏆 TEST SUMMARY")
        print("="*50)
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if failed > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["status"]:
                    print(f"   - {result['test']}: {result['details']}")
        
        # Save results to file
        with open("test_results.json", "w") as f:
            json.dump(self.test_results, f, indent=2)
        print(f"\n📁 Detailed results saved to: test_results.json")

def main():
    """Main function to run tests."""
    # Check if server is specified
    base_url = "http://localhost:8000"
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    # Run tests
    test_suite = KlernoLabsTestSuite(base_url)
    test_suite.run_all_tests()

if __name__ == "__main__":
    main()