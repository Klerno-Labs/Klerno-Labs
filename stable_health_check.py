"""
Stable Health Check Script for Klerno Labs Enterprise Application
Tests endpoints with proper headers to avoid security blocks
"""

import requests
import time
import json
from typing import Dict, List, Optional
import logging

class StableHealthChecker:
    """Health checker that works with enterprise security"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        
        # Configure headers to pass security checks
        self.session.headers.update({
            'User-Agent': 'Klerno-Health-Check/1.0 (Enterprise Monitoring)',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def check_basic_health(self) -> Dict:
        """Check basic server health"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            return {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "content": response.text[:200] if response.text else "No content"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "response_time": 0
            }
    
    def check_root_endpoint(self) -> Dict:
        """Check root endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/", timeout=10)
            return {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "response_time": 0
            }
    
    def check_docs_endpoint(self) -> Dict:
        """Check API documentation endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/docs", timeout=10)
            return {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "response_time": 0
            }
    
    def check_admin_endpoint(self) -> Dict:
        """Check admin dashboard endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/admin/dashboard", timeout=10)
            return {
                "status": "responding" if response.status_code in [200, 302, 401, 403] else "unhealthy",
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "response_time": 0
            }
    
    def run_comprehensive_check(self) -> Dict:
        """Run comprehensive health check"""
        self.logger.info("🔍 Starting comprehensive health check...")
        
        results = {
            "timestamp": time.time(),
            "checks": {}
        }
        
        # Test basic endpoints
        endpoints = [
            ("health", self.check_basic_health),
            ("root", self.check_root_endpoint),
            ("docs", self.check_docs_endpoint),
            ("admin", self.check_admin_endpoint),
        ]
        
        for name, check_func in endpoints:
            self.logger.info(f"Testing {name} endpoint...")
            results["checks"][name] = check_func()
            time.sleep(0.5)  # Brief pause between checks
        
        # Calculate overall health
        healthy_count = sum(1 for check in results["checks"].values() 
                          if check["status"] in ["healthy", "responding"])
        total_count = len(results["checks"])
        
        results["overall_health"] = {
            "status": "healthy" if healthy_count >= total_count * 0.75 else "unhealthy",
            "healthy_endpoints": healthy_count,
            "total_endpoints": total_count,
            "health_percentage": (healthy_count / total_count) * 100
        }
        
        return results
    
    def print_results(self, results: Dict):
        """Print formatted results"""
        print("\n" + "="*60)
        print("🏥 KLERNO LABS - HEALTH CHECK RESULTS")
        print("="*60)
        print(f"⏰ Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(results['timestamp']))}")
        print(f"🌐 Base URL: {self.base_url}")
        print()
        
        # Overall health
        overall = results["overall_health"]
        status_emoji = "✅" if overall["status"] == "healthy" else "❌"
        print(f"{status_emoji} Overall Health: {overall['status'].upper()}")
        print(f"📊 Health Score: {overall['health_percentage']:.1f}% ({overall['healthy_endpoints']}/{overall['total_endpoints']} endpoints)")
        print()
        
        # Individual endpoint results
        print("📍 Endpoint Details:")
        print("-" * 60)
        
        for endpoint, check in results["checks"].items():
            status = check["status"]
            status_emoji = "✅" if status in ["healthy", "responding"] else "❌"
            
            print(f"{status_emoji} {endpoint.upper():<10} | Status: {status:<10} | "
                  f"Code: {check.get('status_code', 'N/A'):<3} | "
                  f"Time: {check.get('response_time', 0):.3f}s")
            
            if "error" in check:
                print(f"   ⚠️  Error: {check['error']}")
        
        print("="*60)

def main():
    """Run health check"""
    checker = StableHealthChecker()
    results = checker.run_comprehensive_check()
    checker.print_results(results)
    
    # Return exit code based on health
    if results["overall_health"]["status"] == "healthy":
        print("✅ All systems operational!")
        return 0
    else:
        print("❌ Some systems need attention!")
        return 1

if __name__ == "__main__":
    exit(main())