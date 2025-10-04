#!/usr/bin/env python3
"""OpenAPI Documentation Validator
Validates that the FastAPI application has comprehensive OpenAPI documentation
"""

import time

import requests


def test_openapi_schema_completeness():
    """Test that OpenAPI schema is complete and well-documented"""
    base_url = "http://localhost:8002"

    print("🔍 OPENAPI SCHEMA VALIDATION")
    print("=" * 50)

    # Test OpenAPI JSON endpoint
    try:
        response = requests.get(f"{base_url}/openapi.json", timeout=30)
        if response.status_code != 200:
            print(f"❌ Failed to fetch OpenAPI schema: {response.status_code}")
            return False

        schema = response.json()
        print("✅ OpenAPI schema fetched successfully")

        # Check basic schema structure
        required_fields = ["openapi", "info", "paths"]
        for field in required_fields:
            if field not in schema:
                print(f"❌ Missing required field: {field}")
                return False

        print("✅ Schema has all required top-level fields")

        # Check info section
        info = schema.get("info", {})
        info_fields = ["title", "version"]
        for field in info_fields:
            if field not in info:
                print(f"❌ Missing info field: {field}")
            else:
                print(f"✅ Info.{field}: {info[field]}")

        # Check paths
        paths = schema.get("paths", {})
        print(f"✅ Total API paths documented: {len(paths)}")

        # Validate key endpoints are documented
        expected_endpoints = [
            "/",
            "/health",
            "/status",
            "/dashboard",
            "/admin",
            "/docs",
            "/premium/advanced-analytics",
            "/enterprise/status",
        ]

        documented_endpoints = []
        missing_endpoints = []

        for endpoint in expected_endpoints:
            if endpoint in paths:
                documented_endpoints.append(endpoint)
                print(f"✅ {endpoint} - documented")
            else:
                missing_endpoints.append(endpoint)
                print(f"❌ {endpoint} - not documented")

        print("\nDocumentation Summary:")
        print(
            f"✅ Documented endpoints: {len(documented_endpoints)}/{len(expected_endpoints)}",
        )
        if missing_endpoints:
            print(f"❌ Missing documentation: {missing_endpoints}")

        # Check if endpoints have proper HTTP methods
        methods_count = {}
        for _path, methods in paths.items():
            for method in methods:
                if method not in ["parameters", "summary", "description"]:
                    methods_count[method.upper()] = (
                        methods_count.get(method.upper(), 0) + 1
                    )

        print("\nHTTP Methods Distribution:")
        for method, count in methods_count.items():
            print(f"✅ {method}: {count} endpoints")

        return len(missing_endpoints) == 0

    except Exception as e:
        print(f"❌ Error testing OpenAPI schema: {e}")
        return False


def test_redoc_documentation():
    """Test that ReDoc documentation is accessible"""
    base_url = "http://localhost:8002"

    print("\n🔍 REDOC DOCUMENTATION VALIDATION")
    print("=" * 50)

    try:
        response = requests.get(f"{base_url}/redoc", timeout=30)
        if response.status_code == 200:
            print("✅ ReDoc documentation accessible")
            print(f"✅ Content length: {len(response.content)} bytes")

            # Check if it contains expected content
            content = response.text.lower()
            expected_content = ["redoc", "api", "documentation"]
            for term in expected_content:
                if term in content:
                    print(f"✅ Contains '{term}' content")
                else:
                    print(f"❌ Missing '{term}' content")

            return True
        print(f"❌ ReDoc not accessible: {response.status_code}")
        return False

    except Exception as e:
        print(f"❌ Error testing ReDoc: {e}")
        return False


def test_swagger_ui():
    """Test that Swagger UI documentation is accessible"""
    base_url = "http://localhost:8002"

    print("\n🔍 SWAGGER UI VALIDATION")
    print("=" * 50)

    try:
        response = requests.get(f"{base_url}/docs", timeout=30)
        if response.status_code == 200:
            print("✅ Swagger UI accessible")
            print(f"✅ Content length: {len(response.content)} bytes")

            # Check if it contains expected content
            content = response.text.lower()
            expected_content = ["swagger", "api", "openapi"]
            for term in expected_content:
                if term in content:
                    print(f"✅ Contains '{term}' content")
                else:
                    print(f"❌ Missing '{term}' content")

            return True
        print(f"❌ Swagger UI not accessible: {response.status_code}")
        return False

    except Exception as e:
        print(f"❌ Error testing Swagger UI: {e}")
        return False


def main():
    print("🚀 KLERNO LABS OPENAPI VALIDATION SUITE")
    print("=" * 60)

    # Check server connectivity
    try:
        response = requests.get("http://localhost:8002/health", timeout=10)
        if response.status_code != 200:
            print("❌ Server not responding. Please start the server first.")
            return
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return

    print("✅ Server is running and responsive\n")

    # Run validation tests
    tests = [
        ("OpenAPI Schema", test_openapi_schema_completeness),
        ("ReDoc Documentation", test_redoc_documentation),
        ("Swagger UI", test_swagger_ui),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        start_time = time.time()
        try:
            result = test_func()
            duration = time.time() - start_time
            results.append((test_name, result, duration))
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{status} in {duration:.2f}s")
        except Exception as e:
            duration = time.time() - start_time
            results.append((test_name, False, duration))
            print(f"❌ FAILED with error: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result, _ in results if result)
    total = len(results)

    for test_name, result, duration in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} {test_name} ({duration:.2f}s)")

    print(f"\n🎯 Overall Result: {passed}/{total} tests passed")
    if passed == total:
        print("🎉 ALL OPENAPI VALIDATION TESTS PASSED!")
    else:
        print(f"⚠️  {total - passed} tests failed")


if __name__ == "__main__":
    main()
