#!/usr/bin/env python3
"""Quick OpenAPI test to check if documentation is accessible"""


import requests


def test_openapi():
    base_url = "http://localhost:8002"

    print("🔍 Quick OpenAPI Documentation Test")
    print("=" * 50)

    endpoints_to_test = ["/openapi.json", "/docs", "/redoc"]

    for endpoint in endpoints_to_test:
        try:
            print(f"Testing {endpoint}...")
            response = requests.get(f"{base_url}{endpoint}", timeout=5)

            if response.status_code == 200:
                print(f"✅ {endpoint} - OK ({len(response.content)} bytes)")

                if endpoint == "/openapi.json":
                    # Quick schema check
                    schema = response.json()
                    paths_count = len(schema.get("paths", {}))
                    print(f"  📊 {paths_count} API paths documented")

            else:
                print(f"❌ {endpoint} - Status: {response.status_code}")

        except Exception as e:
            print(f"❌ {endpoint} - Error: {e}")

    print("\n✅ OpenAPI documentation test completed")


if __name__ == "__main__":
    test_openapi()
