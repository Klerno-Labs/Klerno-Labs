"""
Klerno Labs - Server Test Script
Tests the server endpoints once it's running.
"""

import requests
import time
import sys

def test_server(base_url="http://127.0.0.1:8000", timeout=30):
    """Test server endpoints with retries."""
    print(f"[TEST] Testing server at {base_url}")
    
    # Wait for server to be ready
    print("[TEST] Waiting for server to be ready...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{base_url}/healthz", timeout=5)
            if response.status_code == 200:
                print("[OK] Server is ready!")
                break
        except requests.exceptions.RequestException:
            time.sleep(1)
    else:
        print("[ERROR] Server failed to start within timeout")
        return False
    
    # Test key endpoints
    endpoints = [
        "/healthz",
        "/health", 
        "/api/status",
        "/docs",
        "/"
    ]
    
    print("\n[TEST] Testing endpoints:")
    success_count = 0
    
    for endpoint in endpoints:
        try:
            url = f"{base_url}{endpoint}"
            response = requests.get(url, timeout=10)
            status = "✓" if response.status_code < 400 else "✗"
            print(f"  {status} {endpoint}: {response.status_code}")
            if response.status_code < 400:
                success_count += 1
        except Exception as e:
            print(f"  ✗ {endpoint}: Error - {str(e)[:50]}")
    
    print(f"\n[RESULT] {success_count}/{len(endpoints)} endpoints working")
    return success_count > 0

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Klerno Labs Server")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Base URL to test")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds")
    
    args = parser.parse_args()
    
    success = test_server(args.url, args.timeout)
    sys.exit(0 if success else 1)