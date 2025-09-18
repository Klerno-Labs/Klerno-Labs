"""
Quick Endpoint Validation Script for Klerno Labs
Tests key endpoints with minimal overhead to avoid server shutdown
"""

import requests
import time
import sys

def test_endpoint(url, name, expected_codes=[200], timeout=5):
    """Test a single endpoint quickly"""
    try:
        headers = {
            'User-Agent': 'Klerno-Quick-Test/1.0',
            'Accept': 'text/html,application/json,*/*',
        }
        
        response = requests.get(url, headers=headers, timeout=timeout)
        status = "✅ PASS" if response.status_code in expected_codes else "❌ FAIL"
        
        print(f"{status} {name:<20} | Code: {response.status_code:<3} | Time: {response.elapsed.total_seconds():.3f}s")
        
        return response.status_code in expected_codes
        
    except Exception as e:
        print(f"❌ FAIL {name:<20} | Error: {str(e)[:50]}")
        return False

def main():
    """Run quick endpoint tests"""
    base_url = "http://localhost:8000"  # Back to port 8000
    
    print("🔍 KLERNO LABS - QUICK ENDPOINT VALIDATION")
    print("=" * 55)
    
    # Test critical endpoints
    tests = [
        ("/health", "Health Check", [200]),
        ("/", "Root/Landing", [200]),
        ("/docs", "API Docs", [200]),
        ("/admin/dashboard", "Admin Dashboard", [200, 302, 401, 403]),  # May redirect or require auth
    ]
    
    passed = 0
    total = len(tests)
    
    for path, name, expected in tests:
        if test_endpoint(f"{base_url}{path}", name, expected):
            passed += 1
        time.sleep(0.2)  # Brief pause between tests
    
    print("=" * 55)
    print(f"🎯 Results: {passed}/{total} endpoints responding correctly")
    
    if passed >= total * 0.75:
        print("✅ Server is operational!")
        return 0
    else:
        print("❌ Server needs attention!")
        return 1

if __name__ == "__main__":
    exit(main())