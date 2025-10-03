import time

import requests

# Wait a moment for the server to be ready
time.sleep(2)

print("Testing basic routes for errors")

paths = [
    "/admin/",
    "/auth/login",
    "/auth/signup",
    "/admin/users",
    "/admin/api/stats",
    "/signup",
    "/login",
    "/logout",
    "/paywall",
    "/dashboard",
    "/admin",
    "/health",
    "/healthz",
    "/status",
    "/ready",
    "/favicon.ico",
    "/offline.html",
    "/static/favicon.ico",
    "/static/robots.txt",
    "/static/sw.js",
    "/static/manifest.json",
    "/css/elite.css",
    "/js/main.js",
    "/images/hero-bg.jpg",
    "/static/css/elite.css",
    "/static/js/main.js",
    "/static/images/hero-bg.jpg",
    "/robots.txt",
    "/manifest.json",
    "/sw.js",
    "/.well-known/security.txt",
    "/api/status",
    "/api/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/enterprise/dashboard",
    "/enterprise/status",
    "/premium/advanced-analytics",
]

errors_404 = []
errors_302 = []
success_200 = []
other_codes = []

for p in paths:
    try:
        r = requests.get(f"http://localhost:8002{p}", timeout=3)
        status_code = r.status_code

        if status_code == 404:
            errors_404.append(p)
        elif status_code == 302:
            errors_302.append(p)
        elif status_code == 200:
            success_200.append(p)
        else:
            other_codes.append((p, status_code))

        print(f"{p}: {status_code}")
    except requests.exceptions.RequestException as e:
        print(f"{p}: ERROR - {e}")

print("\n=== 404 ERRORS ===")
for p in errors_404:
    print(f"404: {p}")

print("\n=== 302 REDIRECTS ===")
for p in errors_302:
    print(f"302: {p}")

print("\n=== OTHER STATUS CODES ===")
for p, code in other_codes:
    print(f"{code}: {p}")

print("\n=== SUMMARY ===")
print(f"Total 404 errors: {len(errors_404)}")
print(f"Total 302 redirects: {len(errors_302)}")
print(f"Total 200 success: {len(success_200)}")
print(f"Total other codes: {len(other_codes)}")
