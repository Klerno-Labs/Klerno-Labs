#!/usr/bin/env python3
"""
Comprehensive QA Audit Script for Klerno Labs
Performs systematic testing of all endpoints, links, and functionality
"""

import requests
import time
import json
from typing import Dict, List, Tuple
from urllib.parse import urljoin, urlparse

class KlernoQAAudit:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = {
            "endpoints": {},
            "static_files": {},
            "forms": {},
            "errors": [],
            "warnings": []
        }
    
    def test_endpoint(self, path: str, method: str = "GET", expected_status: int = 200) -> Dict:
        """Test a single endpoint and return results"""
        url = urljoin(self.base_url, path)
        try:
            response = self.session.request(method, url, timeout=10)
            result = {
                "url": url,
                "status_code": response.status_code,
                "success": response.status_code == expected_status,
                "response_time": response.elapsed.total_seconds(),
                "content_type": response.headers.get("content-type", ""),
                "content_length": len(response.content)
            }
            
            if response.status_code != expected_status:
                self.results["errors"].append(f"{method} {path} returned {response.status_code}, expected {expected_status}")
            
            return result
            
        except requests.exceptions.RequestException as e:
            error_result = {
                "url": url,
                "status_code": None,
                "success": False,
                "error": str(e),
                "response_time": None
            }
            self.results["errors"].append(f"{method} {path} failed: {str(e)}")
            return error_result
    
    def test_core_routes(self):
        """Test all core application routes"""
        core_routes = [
            # Public routes
            ("/", 200),
            ("/healthz", 200),
            ("/status", 200),
            ("/docs", 200),
            ("/demo", 200),
            
            # Auth routes
            ("/auth/login", 200),
            ("/auth/signup", 200),
            ("/signup", 302),  # Should redirect
            
            # Static files
            ("/static/css/design-system.css", 200),
            ("/static/klerno-logo.png", 200),
            ("/static/favicon.ico", 200),
            
            # Protected routes (should redirect or 401/403)
            ("/dashboard", 401),
            ("/alerts-ui", 401),
            ("/wallets", 401),
            
            # Admin routes
            ("/admin/dashboard", 401),
            
            # API routes
            ("/api/health", 200),
        ]
        
        print("🔍 Testing Core Routes...")
        for route, expected_status in core_routes:
            result = self.test_endpoint(route, expected_status=expected_status)
            self.results["endpoints"][route] = result
            status_icon = "✅" if result["success"] else "❌"
            print(f"  {status_icon} {route} -> {result.get('status_code', 'ERROR')}")
    
    def test_error_pages(self):
        """Test custom error pages"""
        print("\n🔍 Testing Error Pages...")
        
        # Test 404
        result_404 = self.test_endpoint("/nonexistent-page", expected_status=404)
        self.results["endpoints"]["/404-test"] = result_404
        
        # Test if we have custom error pages
        if result_404.get("content_type", "").startswith("text/html"):
            print("  ✅ Custom 404 page detected")
        else:
            self.results["warnings"].append("No custom 404 page found")
            print("  ⚠️ No custom 404 page found")
    
    def generate_sitemap(self):
        """Generate a sitemap of all discovered routes"""
        print("\n🗺️ Generating Route Sitemap...")
        
        working_routes = []
        broken_routes = []
        
        for route, result in self.results["endpoints"].items():
            if result["success"]:
                working_routes.append(route)
            else:
                broken_routes.append(route)
        
        sitemap = {
            "working_routes": sorted(working_routes),
            "broken_routes": sorted(broken_routes),
            "total_routes": len(self.results["endpoints"]),
            "success_rate": len(working_routes) / len(self.results["endpoints"]) * 100
        }
        
        print(f"  📊 Total Routes: {sitemap['total_routes']}")
        print(f"  ✅ Working: {len(working_routes)}")
        print(f"  ❌ Broken: {len(broken_routes)}")
        print(f"  📈 Success Rate: {sitemap['success_rate']:.1f}%")
        
        return sitemap
    
    def run_audit(self):
        """Run the complete audit"""
        print("🚀 Starting Klerno Labs QA Audit...\n")
        
        # Test if server is running
        try:
            response = self.session.get(self.base_url, timeout=5)
            print(f"✅ Server is running at {self.base_url}")
        except requests.exceptions.RequestException:
            print(f"❌ Server is not responding at {self.base_url}")
            return False
        
        # Run tests
        self.test_core_routes()
        self.test_error_pages()
        sitemap = self.generate_sitemap()
        
        # Summary
        print("\n📋 AUDIT SUMMARY")
        print("=" * 50)
        print(f"Errors Found: {len(self.results['errors'])}")
        print(f"Warnings: {len(self.results['warnings'])}")
        
        if self.results["errors"]:
            print("\n❌ ERRORS:")
            for error in self.results["errors"]:
                print(f"  • {error}")
        
        if self.results["warnings"]:
            print("\n⚠️ WARNINGS:")
            for warning in self.results["warnings"]:
                print(f"  • {warning}")
        
        if not self.results["errors"]:
            print("\n🎉 NO CRITICAL ERRORS FOUND!")
        
        return True

if __name__ == "__main__":
    auditor = KlernoQAAudit()
    auditor.run_audit()