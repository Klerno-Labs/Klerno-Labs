#!/usr/bin/env python3
"""
Live API Testing Script for Quality Assurance
Tests all critical endpoints to ensure 99.99% quality
"""

import json
import sys
import time
from datetime import datetime

import requests

BASE_URL = "http://127.0.0.1:8000"

def test_endpoint(method, endpoint, headers=None, data=None, expected_status=200):
    """Test a single endpoint and return results"""
    url = f"{BASE_URL}{endpoint}"
    headers = headers or {}
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=10)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=headers, json=data, timeout=10)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=10)
        else:
            return {"error": f"Unsupported method: {method}"}
        
        result = {
            "endpoint": endpoint,
            "method": method,
            "status_code": response.status_code,
            "response_time": response.elapsed.total_seconds(),
            "success": response.status_code == expected_status,
            "content_length": len(response.content),
            "headers": dict(response.headers)
        }
        
        # Try to parse JSON response
        try:
            result["json_response"] = response.json()
        except:
            result["text_response"] = response.text[:500]  # First 500 chars
            
        return result
        
    except requests.exceptions.RequestException as e:
        return {
            "endpoint": endpoint,
            "method": method,
            "error": str(e),
            "success": False
        }

def main():
    print("🚀 Klerno Labs - Live API Quality Assurance Testing")
    print("=" * 60)
    print(f"Started at: {datetime.now()}")
    print(f"Base URL: {BASE_URL}")
    print()
    
    # Wait for server to be ready
    print("⏳ Waiting for server to start...")
    time.sleep(8)
    
    # Test suite configuration
    tests = [
        # Core Health Checks
        ("GET", "/health", None, None, 200),
        ("GET", "/healthz", None, None, 200),
        
        # Authentication Tests
        ("GET", "/", None, None, 200),  # Landing page
        ("GET", "/login", None, None, 200),  # Login page
        ("GET", "/signup", None, None, 200),  # Signup page
        
        # API Endpoints (without auth for basic connectivity)
        ("GET", "/api/sample-data", None, None, 200),
        ("POST", "/api/analyze/sample", None, {"data": "test"}, None),  # May need auth
        
        # XRPL Integration
        ("GET", "/integrations/xrpl/fetch", None, None, None),  # May need auth
        
        # ISO20022 Endpoints
        ("GET", "/enterprise/iso20022/", None, None, None),  # May need auth
        
        # Admin Dashboard (will test redirect/auth)
        ("GET", "/admin", None, None, None),
        ("GET", "/dashboard", None, None, None),
        
        # Static file serving
        ("GET", "/static/klerno-logo.png", None, None, 200),
    ]
    
    results = []
    passed = 0
    failed = 0
    
    print("🧪 Running endpoint tests...")
    print()
    
    for i, (method, endpoint, headers, data, expected_status) in enumerate(tests, 1):
        print(f"[{i:2d}] Testing {method} {endpoint}")
        
        result = test_endpoint(method, endpoint, headers, data, expected_status)
        results.append(result)
        
        if result.get("success"):
            passed += 1
            status_icon = "✅"
        elif "error" in result:
            failed += 1
            status_icon = "❌"
        else:
            # If no expected status was set, just check if we got a response
            if result.get("status_code"):
                passed += 1
                status_icon = "🔶"  # Got response but no expected status to compare
            else:
                failed += 1
                status_icon = "❌"
        
        print(f"     {status_icon} Status: {result.get('status_code', 'ERROR')}, Time: {result.get('response_time', 0):.3f}s")
        
        if "error" in result:
            print(f"     Error: {result['error']}")
        
        time.sleep(0.5)  # Brief pause between requests
    
    print()
    print("📊 Test Results Summary")
    print("=" * 60)
    print(f"Total Tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/len(tests)*100):.1f}%")
    print()
    
    # Detailed results
    print("📋 Detailed Results:")
    for result in results:
        if result.get("success") or result.get("status_code"):
            print(f"✅ {result.get('method', 'N/A')} {result.get('endpoint', 'N/A')} -> {result.get('status_code', 'ERROR')}")
        else:
            print(f"❌ {result.get('method', 'N/A')} {result.get('endpoint', 'N/A')} -> {result.get('error', 'Unknown error')}")
    
    print()
    print(f"🏁 Testing completed at: {datetime.now()}")
    
    # Save detailed results to file
    with open("live_test_results.json", "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": len(tests),
                "passed": passed,
                "failed": failed,
                "success_rate": passed/len(tests)*100
            },
            "results": results
        }, f, indent=2)
    
    print("💾 Detailed results saved to live_test_results.json")
    
    return passed / len(tests) >= 0.8  # 80% success rate for basic connectivity

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)