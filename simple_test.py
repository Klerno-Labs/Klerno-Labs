#!/usr/bin/env python3
"""
Quick Manual QA Test Script for Klerno Labs
Tests key endpoints one by one
"""
import subprocess
import time
import os
import sys

def test_route_simple(route, expected_text=None):
    """Test a route using curl"""
    try:
        cmd = f'curl -s -w "HTTPSTATUS:%{{http_code}}" http://127.0.0.1:8000{route}'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        
        output = result.stdout
        if "HTTPSTATUS:" in output:
            content, status = output.rsplit("HTTPSTATUS:", 1)
            status_code = int(status.strip())
            
            if expected_text and expected_text.lower() not in content.lower():
                return False, f"Status {status_code} but missing expected text '{expected_text}'"
            
            return status_code < 400, f"Status {status_code}"
        else:
            return False, f"No status code returned: {output[:100]}"
            
    except Exception as e:
        return False, f"Error: {str(e)}"

def main():
    print("🔍 Quick QA Test for Klerno Labs")
    print("=" * 50)
    
    # Test routes
    routes_to_test = [
        ("/", "Klerno Labs"),
        ("/healthz", None),
        ("/auth/login", "login"),
        ("/auth/signup", "signup"),
        ("/static/klerno-logo.png", None),
        ("/docs", None),
        ("/demo", "demo"),
        ("/nonexistent", None)  # Should 404
    ]
    
    passed = 0
    failed = 0
    
    for route, expected_text in routes_to_test:
        success, message = test_route_simple(route, expected_text)
        status = "✅" if success else "❌"
        print(f"{status} {route:<20} | {message}")
        
        if success:
            passed += 1
        else:
            failed += 1
        
        time.sleep(0.5)  # Brief pause between requests
    
    print(f"\n📊 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All basic tests passed!")
    else:
        print("⚠️ Some tests failed - see above for details")

if __name__ == "__main__":
    main()