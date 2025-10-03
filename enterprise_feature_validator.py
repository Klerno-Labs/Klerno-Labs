#!/usr/bin/env python3
"""
Enterprise Feature Validation Test
Comprehensive testing of all enterprise features and analytics endpoints
"""

import json
import time
from typing import Any, Dict

import requests

BASE_URL = "http://127.0.0.1:8002"


class EnterpriseFeatureValidator:
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = 10
        self.results = {
            "enterprise_endpoints": {},
            "analytics_features": {},
            "admin_features": {},
            "premium_features": {},
            "security_features": {},
            "api_documentation": {},
        }

    def test_server_availability(self) -> bool:
        """Test if enterprise server is running and responding"""
        try:
            response = self.session.get(f"{BASE_URL}/health")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Server not available: {e}")
            return False

    def test_enterprise_endpoints(self):
        """Test all enterprise-specific endpoints"""
        print("🔍 Testing Enterprise Endpoints...")

        enterprise_routes = [
            "/enterprise/dashboard",
            "/enterprise/status",
            "/admin/api/stats",
            "/premium/advanced-analytics",
        ]

        for route in enterprise_routes:
            try:
                start_time = time.time()
                response = self.session.get(f"{BASE_URL}{route}")
                end_time = time.time()

                self.results["enterprise_endpoints"][route] = {
                    "status_code": response.status_code,
                    "response_time": end_time - start_time,
                    "content_length": len(response.content),
                    "success": response.status_code == 200,
                }

                status = "✅" if response.status_code == 200 else "❌"
                print(
                    f"  {status} {route}: {response.status_code} ({end_time - start_time:.3f}s)"
                )

                # Try to parse JSON response for enterprise endpoints
                if (
                    response.status_code == 200
                    and "application/json" in response.headers.get("content-type", "")
                ):
                    try:
                        data = response.json()
                        self.results["enterprise_endpoints"][route]["has_json"] = True
                        self.results["enterprise_endpoints"][route]["json_keys"] = (
                            list(data.keys()) if isinstance(data, dict) else []
                        )
                    except:
                        self.results["enterprise_endpoints"][route]["has_json"] = False

            except Exception as e:
                print(f"  ❌ {route}: Error - {e}")
                self.results["enterprise_endpoints"][route] = {
                    "status_code": 0,
                    "error": str(e),
                    "success": False,
                }

    def test_analytics_features(self):
        """Test analytics and reporting features"""
        print("📊 Testing Analytics Features...")

        analytics_routes = [
            "/premium/advanced-analytics",
            "/admin/api/stats",
            "/api/health",
            "/api/status",
        ]

        for route in analytics_routes:
            try:
                response = self.session.get(f"{BASE_URL}{route}")

                self.results["analytics_features"][route] = {
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                }

                if response.status_code == 200:
                    try:
                        data = response.json()
                        # Check for analytics-specific keys
                        analytics_keys = [
                            "analytics_data",
                            "total_volume",
                            "transaction_trends",
                            "risk_metrics",
                            "compliance_score",
                            "total_users",
                            "active_sessions",
                            "system_health",
                        ]

                        found_keys = []
                        if isinstance(data, dict):
                            for key in analytics_keys:
                                if key in data or any(
                                    key in str(v) for v in data.values()
                                ):
                                    found_keys.append(key)

                        self.results["analytics_features"][route][
                            "analytics_keys"
                        ] = found_keys
                        print(
                            f"  ✅ {route}: Found {len(found_keys)} analytics indicators"
                        )

                    except:
                        print(f"  ⚠️  {route}: Non-JSON response")
                else:
                    print(f"  ❌ {route}: Status {response.status_code}")

            except Exception as e:
                print(f"  ❌ {route}: Error - {e}")

    def test_admin_features(self):
        """Test admin panel and management features"""
        print("👨‍💼 Testing Admin Features...")

        admin_routes = ["/admin", "/admin/users", "/admin/api/stats"]

        for route in admin_routes:
            try:
                response = self.session.get(f"{BASE_URL}{route}")

                self.results["admin_features"][route] = {
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "content_type": response.headers.get("content-type", ""),
                    "has_admin_content": False,
                }

                # Check for admin-specific content
                content = response.text.lower()
                admin_indicators = [
                    "admin",
                    "dashboard",
                    "users",
                    "management",
                    "statistics",
                    "system",
                    "enterprise",
                ]

                found_indicators = [ind for ind in admin_indicators if ind in content]
                self.results["admin_features"][route][
                    "admin_indicators"
                ] = found_indicators
                self.results["admin_features"][route]["has_admin_content"] = (
                    len(found_indicators) > 0
                )

                status = "✅" if response.status_code == 200 else "❌"
                print(
                    f"  {status} {route}: {response.status_code} (admin indicators: {len(found_indicators)})"
                )

            except Exception as e:
                print(f"  ❌ {route}: Error - {e}")

    def test_premium_features(self):
        """Test premium and advanced features"""
        print("💎 Testing Premium Features...")

        premium_routes = ["/premium/advanced-analytics"]

        for route in premium_routes:
            try:
                response = self.session.get(f"{BASE_URL}{route}")

                self.results["premium_features"][route] = {
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                }

                if response.status_code == 200:
                    try:
                        data = response.json()

                        # Check for premium feature indicators
                        premium_keys = [
                            "advanced",
                            "analytics",
                            "premium",
                            "enterprise",
                            "compliance_score",
                            "risk_metrics",
                            "trends",
                        ]

                        found_premium_keys = []
                        content_str = json.dumps(data).lower()

                        for key in premium_keys:
                            if key in content_str:
                                found_premium_keys.append(key)

                        self.results["premium_features"][route][
                            "premium_indicators"
                        ] = found_premium_keys
                        print(
                            f"  ✅ {route}: Found {len(found_premium_keys)} premium indicators"
                        )

                    except:
                        print(f"  ⚠️  {route}: Non-JSON response")
                else:
                    print(f"  ❌ {route}: Status {response.status_code}")

            except Exception as e:
                print(f"  ❌ {route}: Error - {e}")

    def test_security_features(self):
        """Test security endpoints and features"""
        print("🔒 Testing Security Features...")

        security_routes = ["/.well-known/security.txt", "/health", "/status"]

        for route in security_routes:
            try:
                response = self.session.get(f"{BASE_URL}{route}")

                self.results["security_features"][route] = {
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "has_security_headers": False,
                    "security_headers": [],
                }

                # Check for security headers
                security_headers = [
                    "x-content-type-options",
                    "x-frame-options",
                    "x-xss-protection",
                    "strict-transport-security",
                    "content-security-policy",
                ]

                found_headers = []
                for header in security_headers:
                    if header in response.headers:
                        found_headers.append(header)

                self.results["security_features"][route][
                    "security_headers"
                ] = found_headers
                self.results["security_features"][route]["has_security_headers"] = (
                    len(found_headers) > 0
                )

                status = "✅" if response.status_code == 200 else "❌"
                print(
                    f"  {status} {route}: {response.status_code} (security headers: {len(found_headers)})"
                )

            except Exception as e:
                print(f"  ❌ {route}: Error - {e}")

    def test_api_documentation(self):
        """Test API documentation endpoints"""
        print("📚 Testing API Documentation...")

        doc_routes = ["/docs", "/redoc", "/openapi.json"]

        for route in doc_routes:
            try:
                response = self.session.get(f"{BASE_URL}{route}")

                self.results["api_documentation"][route] = {
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "content_type": response.headers.get("content-type", ""),
                    "content_length": len(response.content),
                }

                # For OpenAPI JSON, validate it's valid JSON
                if route == "/openapi.json" and response.status_code == 200:
                    try:
                        openapi_data = response.json()
                        self.results["api_documentation"][route][
                            "is_valid_openapi"
                        ] = True
                        self.results["api_documentation"][route]["openapi_version"] = (
                            openapi_data.get("openapi", "unknown")
                        )
                        self.results["api_documentation"][route]["path_count"] = len(
                            openapi_data.get("paths", {})
                        )
                        print(
                            f"  ✅ {route}: Valid OpenAPI v{openapi_data.get('openapi', 'unknown')} with {len(openapi_data.get('paths', {}))} paths"
                        )
                    except:
                        self.results["api_documentation"][route][
                            "is_valid_openapi"
                        ] = False
                        print(f"  ⚠️  {route}: Invalid JSON")
                else:
                    status = "✅" if response.status_code == 200 else "❌"
                    print(f"  {status} {route}: {response.status_code}")

            except Exception as e:
                print(f"  ❌ {route}: Error - {e}")

    def generate_summary_report(self):
        """Generate comprehensive summary report"""
        print("\n" + "=" * 80)
        print("ENTERPRISE FEATURE VALIDATION REPORT")
        print("=" * 80)

        # Calculate overall metrics
        total_endpoints = 0
        successful_endpoints = 0

        for category, endpoints in self.results.items():
            category_total = len(endpoints)
            category_success = sum(
                1 for ep in endpoints.values() if ep.get("success", False)
            )

            total_endpoints += category_total
            successful_endpoints += category_success

            success_rate = (
                (category_success / category_total * 100) if category_total > 0 else 0
            )

            print(f"\n📋 {category.replace('_', ' ').title()}:")
            print(
                f"   Success Rate: {success_rate:.1f}% ({category_success}/{category_total})"
            )

            # Show details for each endpoint
            for endpoint, data in endpoints.items():
                status = "✅" if data.get("success", False) else "❌"
                response_time = data.get("response_time", 0)
                time_str = f" ({response_time:.3f}s)" if response_time > 0 else ""
                print(
                    f"   {status} {endpoint}: {data.get('status_code', 'N/A')}{time_str}"
                )

        # Overall summary
        overall_success_rate = (
            (successful_endpoints / total_endpoints * 100) if total_endpoints > 0 else 0
        )

        print(f"\n🎯 OVERALL SUMMARY:")
        print(f"   Total Endpoints Tested: {total_endpoints}")
        print(f"   Successful Endpoints: {successful_endpoints}")
        print(f"   Overall Success Rate: {overall_success_rate:.1f}%")

        # Performance summary
        all_response_times = []
        for category_data in self.results.values():
            for endpoint_data in category_data.values():
                if "response_time" in endpoint_data:
                    all_response_times.append(endpoint_data["response_time"])

        if all_response_times:
            avg_response_time = sum(all_response_times) / len(all_response_times)
            max_response_time = max(all_response_times)
            print(f"   Average Response Time: {avg_response_time:.3f}s")
            print(f"   Maximum Response Time: {max_response_time:.3f}s")

        # Recommendations
        print(f"\n💡 ASSESSMENT:")
        if overall_success_rate >= 95:
            print("   🏆 EXCELLENT - Enterprise platform is production ready!")
        elif overall_success_rate >= 90:
            print("   ✅ GOOD - Enterprise platform is mostly functional")
        elif overall_success_rate >= 80:
            print("   ⚠️  ACCEPTABLE - Some issues need attention")
        else:
            print("   ❌ NEEDS WORK - Significant issues require fixing")

        return overall_success_rate

    def run_all_tests(self):
        """Run complete enterprise feature validation"""
        print("🚀 Starting Enterprise Feature Validation...")
        print("=" * 60)

        if not self.test_server_availability():
            return False

        print("✅ Enterprise server is running\n")

        # Run all test categories
        self.test_enterprise_endpoints()
        print()
        self.test_analytics_features()
        print()
        self.test_admin_features()
        print()
        self.test_premium_features()
        print()
        self.test_security_features()
        print()
        self.test_api_documentation()

        # Generate final report
        overall_success_rate = self.generate_summary_report()

        return overall_success_rate >= 90


def main():
    validator = EnterpriseFeatureValidator()
    success = validator.run_all_tests()

    if success:
        print("\n🎉 Enterprise feature validation completed successfully!")
        exit(0)
    else:
        print("\n⚠️  Enterprise feature validation found issues.")
        exit(1)


if __name__ == "__main__":
    main()
