#!/usr/bin/env python3
"""
Simple Server Status Checker for Klerno Labs
"""

import requests
import time
import json

def check_server_status():
    """Check if the Klerno Labs server is running and responding"""
    server_url = "http://127.0.0.1:8000"
    
    endpoints = {
        "Health Check": "/healthz",
        "API Health": "/health", 
        "Metrics": "/metrics",
        "Documentation": "/docs",
        "ReDoc": "/redoc"
    }
    
    print("🔍 Klerno Labs Server Status Check")
    print("=" * 50)
    
    # Test each endpoint
    results = {}
    total_success = 0
    
    for name, endpoint in endpoints.items():
        try:
            start_time = time.time()
            response = requests.get(f"{server_url}{endpoint}", timeout=5)
            duration = (time.time() - start_time) * 1000
            
            success = response.status_code < 400
            if success:
                total_success += 1
                
            status_icon = "✅" if success else "❌"
            print(f"{status_icon} {name:15} [{response.status_code:3d}] {duration:6.2f}ms - {endpoint}")
            
            results[name] = {
                "status_code": response.status_code,
                "duration_ms": round(duration, 2),
                "success": success,
                "url": f"{server_url}{endpoint}"
            }
            
        except requests.RequestException as e:
            print(f"❌ {name:15} [ERR] Connection failed - {endpoint}")
            results[name] = {
                "error": str(e),
                "success": False,
                "url": f"{server_url}{endpoint}"
            }
    
    print("=" * 50)
    print(f"📊 Overall Status: {total_success}/{len(endpoints)} endpoints responding")
    
    if total_success == len(endpoints):
        print("✅ Server is fully operational!")
    elif total_success > 0:
        print("⚠️  Server is partially operational")
    else:
        print("❌ Server appears to be down")
    
    print(f"🌐 Server URL: {server_url}")
    print(f"📋 Admin Dashboard: {server_url}/admin/dashboard")
    
    return results

def quick_health_check():
    """Quick health check"""
    try:
        response = requests.get("http://127.0.0.1:8000/healthz", timeout=3)
        if response.status_code == 200:
            print("✅ Server is running and healthy!")
            return True
        else:
            print(f"⚠️  Server responded with status {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"❌ Server is not responding: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        quick_health_check()
    else:
        check_server_status()