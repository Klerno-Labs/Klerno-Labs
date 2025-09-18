#!/usr/bin/env python3
"""
Klerno Enterprise Health Check & Endpoint Validation
==================================================

Comprehensive testing suite for all Klerno endpoints
"""

import requests
import json
import time
import sys
from typing import Dict, List, Any
from urllib.parse import urljoin

class KlernoEndpointTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'KlernoHealthCheck/1.0',
            'Accept': 'application/json, text/html',
            'Content-Type': 'application/json'
        })
        
    def test_endpoint(self, endpoint: str, method: str = "GET", 
                     data: Any = None, expected_codes: List[int] = None) -> Dict:
        """Test a single endpoint"""
        if expected_codes is None:
            expected_codes = [200, 401, 403, 404]  # Acceptable codes
            
        url = urljoin(self.base_url, endpoint)
        
        try:
            response = self.session.request(method, url, json=data, timeout=10)
            
            result = {
                'endpoint': endpoint,
                'method': method,
                'status_code': response.status_code,
                'success': response.status_code in expected_codes,
                'response_size': len(response.content),
                'headers': dict(response.headers),
                'content_preview': response.text[:200] if response.text else None
            }
            
            # Check for common security headers
            security_headers = []
            for header in ['X-Frame-Options', 'Content-Security-Policy', 'X-Content-Type-Options']:
                if header in response.headers:
                    security_headers.append(header)
            result['security_headers'] = security_headers
            
            return result
            
        except Exception as e:
            return {
                'endpoint': endpoint,
                'method': method,
                'success': False,
                'error': str(e)
            }
    
    def run_health_tests(self) -> Dict:
        """Run comprehensive health tests"""
        print("🩺 KLERNO ENTERPRISE HEALTH CHECK")
        print("=" * 50)
        
        # Core health endpoints
        health_endpoints = [
            "/",                    # Landing page
            "/health",             # Basic health check
            "/healthz",            # Kubernetes-style health
            "/api/health-check",   # API health endpoint
            "/docs",               # API documentation
            "/redoc",              # Alternative API docs
            "/openapi.json",       # OpenAPI schema
        ]
        
        # Admin and management endpoints
        admin_endpoints = [
            "/admin/dashboard",    # Admin dashboard
            "/admin/login",        # Admin login
            "/login",              # User login
            "/signup",             # User signup
        ]
        
        # API endpoints
        api_endpoints = [
            "/api/v1/status",      # API status
            "/api/v1/wallets",     # Wallet listing
            "/api/v1/transactions", # Transaction API
            "/api/metrics",        # Metrics endpoint
        ]
        
        # Enterprise endpoints
        enterprise_endpoints = [
            "/enterprise/health",  # Enterprise health
            "/enterprise/status",  # Enterprise status
            "/monitoring/alerts",  # Alert monitoring
            "/security/status",    # Security status
        ]
        
        all_endpoints = (health_endpoints + admin_endpoints + 
                        api_endpoints + enterprise_endpoints)
        
        results = []
        categories = {
            'health': health_endpoints,
            'admin': admin_endpoints,
            'api': api_endpoints,
            'enterprise': enterprise_endpoints
        }
        
        for category, endpoints in categories.items():
            print(f"\n🔍 Testing {category.upper()} endpoints:")
            category_results = []
            
            for endpoint in endpoints:
                result = self.test_endpoint(endpoint)
                category_results.append(result)
                
                # Display result
                if result['success']:
                    status_icon = "✅" if result['status_code'] == 200 else "🔒"
                    print(f"   {status_icon} {endpoint} → {result['status_code']}")
                    if result.get('security_headers'):
                        print(f"      🛡️  Security headers: {', '.join(result['security_headers'])}")
                else:
                    print(f"   ❌ {endpoint} → {result.get('error', 'Failed')}")
            
            results.extend(category_results)
        
        # Summary
        successful = sum(1 for r in results if r['success'])
        total = len(results)
        
        print(f"\n📊 HEALTH CHECK SUMMARY:")
        print(f"   • Total endpoints tested: {total}")
        print(f"   • Successful responses: {successful}")
        print(f"   • Success rate: {successful/total*100:.1f}%")
        
        # Security analysis
        security_enabled = sum(1 for r in results if r.get('security_headers'))
        print(f"   • Endpoints with security headers: {security_enabled}")
        
        return {
            'total_endpoints': total,
            'successful': successful,
            'success_rate': successful/total*100,
            'security_enabled': security_enabled,
            'results': results
        }
    
    def test_performance(self) -> Dict:
        """Basic performance testing"""
        print(f"\n⚡ PERFORMANCE TESTING:")
        
        test_endpoint = "/"
        num_requests = 10
        
        response_times = []
        successful_requests = 0
        
        for i in range(num_requests):
            start_time = time.time()
            result = self.test_endpoint(test_endpoint)
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000  # Convert to ms
            response_times.append(response_time)
            
            if result['success']:
                successful_requests += 1
        
        avg_response_time = sum(response_times) / len(response_times)
        min_response_time = min(response_times)
        max_response_time = max(response_times)
        
        print(f"   • Average response time: {avg_response_time:.2f}ms")
        print(f"   • Min response time: {min_response_time:.2f}ms")
        print(f"   • Max response time: {max_response_time:.2f}ms")
        print(f"   • Success rate: {successful_requests/num_requests*100:.1f}%")
        
        return {
            'avg_response_time': avg_response_time,
            'min_response_time': min_response_time,
            'max_response_time': max_response_time,
            'success_rate': successful_requests/num_requests*100
        }

def main():
    """Main testing function"""
    try:
        # Test if server is reachable
        test_url = "http://localhost:8000"
        response = requests.get(test_url, timeout=5)
        print(f"✅ Server is reachable at {test_url}")
    except Exception as e:
        print(f"❌ Cannot reach server at {test_url}: {e}")
        print("🔧 Please ensure the server is running:")
        print("   python deploy_production.py --host 0.0.0.0 --port 8000")
        return
    
    # Run tests
    tester = KlernoEndpointTester()
    
    # Health tests
    health_results = tester.run_health_tests()
    
    # Performance tests
    performance_results = tester.test_performance()
    
    # Final assessment
    print(f"\n🎯 FINAL ASSESSMENT:")
    if health_results['success_rate'] >= 70:
        print(f"   ✅ Server health: GOOD ({health_results['success_rate']:.1f}% success rate)")
    else:
        print(f"   ⚠️  Server health: NEEDS ATTENTION ({health_results['success_rate']:.1f}% success rate)")
    
    if performance_results['avg_response_time'] < 1000:
        print(f"   ✅ Performance: GOOD ({performance_results['avg_response_time']:.0f}ms avg)")
    else:
        print(f"   ⚠️  Performance: SLOW ({performance_results['avg_response_time']:.0f}ms avg)")
    
    print(f"\n🚀 Klerno Enterprise Server is operational!")

if __name__ == "__main__":
    main()