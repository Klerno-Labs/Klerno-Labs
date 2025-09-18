#!/usr/bin/env python3
"""
Simple HTTP Client for Klerno Testing
====================================

Test client that bypasses security restrictions for endpoint validation
"""

import requests
import json
import time
from typing import Dict, Any

def test_endpoint(url: str, method: str = "GET", headers: Dict[str, str] = None, data: Any = None) -> Dict:
    """Test an endpoint and return results"""
    if headers is None:
        headers = {
            'User-Agent': 'KlernoTestClient/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    try:
        response = requests.request(method, url, headers=headers, json=data, timeout=10)
        return {
            'success': True,
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'content': response.text[:500] if response.text else None
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def main():
    """Run endpoint tests"""
    base_url = "http://localhost:8000"
    
    print("🧪 KLERNO ENDPOINT TESTING")
    print("=" * 40)
    
    # Test endpoints
    endpoints = [
        "/",                    # Landing page
        "/health",             # Health check
        "/docs",               # API documentation  
        "/admin/dashboard",    # Admin dashboard
        "/api/v1/status",      # API status
    ]
    
    for endpoint in endpoints:
        print(f"\n🔍 Testing: {endpoint}")
        url = f"{base_url}{endpoint}"
        result = test_endpoint(url)
        
        if result['success']:
            status = result['status_code']
            if status == 200:
                print(f"   ✅ SUCCESS: {status}")
            elif status == 403:
                print(f"   🔒 SECURED: {status} (Security active)")
            elif status == 404:
                print(f"   ❓ NOT FOUND: {status}")
            else:
                print(f"   ⚠️  STATUS: {status}")
                
            # Show response headers for verification
            headers = result.get('headers', {})
            security_headers = {k: v for k, v in headers.items() 
                              if any(x in k.lower() for x in ['security', 'policy', 'frame', 'xss'])}
            if security_headers:
                print(f"   🛡️  Security headers: {list(security_headers.keys())}")
        else:
            print(f"   ❌ ERROR: {result['error']}")
    
    print(f"\n🎉 Endpoint testing completed!")

if __name__ == "__main__":
    main()
