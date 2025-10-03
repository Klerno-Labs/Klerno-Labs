"""Test all routes using TestClient to identify 404 and 302 errors."""
import importlib
import sys
from fastapi.testclient import TestClient

# Import the enterprise app
sys.path.insert(0, ".")
enterprise_module = importlib.import_module("enterprise_main_v2")
app = enterprise_module.app
client = TestClient(app)

print('Testing basic routes for errors')

paths = [
    "/", "/dashboard", "/admin", "/signup", "/login", "/auth/login", "/auth/signup",
    "/admin/", "/admin/users", "/admin/api/stats", "/logout", "/paywall", 
    "/health", "/healthz", "/status", "/ready", "/favicon.ico", "/offline.html",
    "/static/favicon.ico", "/static/robots.txt", "/static/sw.js", "/static/manifest.json",
    "/css/elite.css", "/js/main.js", "/images/hero-bg.jpg",
    "/static/css/elite.css", "/static/js/main.js", "/static/images/hero-bg.jpg",
    "/robots.txt", "/manifest.json", "/sw.js", "/.well-known/security.txt",
    "/api/status", "/api/health", "/docs", "/redoc", "/openapi.json",
    "/enterprise/dashboard", "/enterprise/status", "/premium/advanced-analytics"
]

errors_404 = []
errors_302 = []
success_200 = []
other_codes = []

for path in paths:
    try:
        response = client.get(path)
        status_code = response.status_code
        
        if status_code == 404:
            errors_404.append(path)
        elif status_code == 302:
            errors_302.append(path)
        elif status_code == 200:
            success_200.append(path)
        else:
            other_codes.append((path, status_code))
            
        print(f'{path}: {status_code}')
        
    except Exception as e:
        print(f'{path}: ERROR - {e}')

print("\n=== 404 ERRORS ===")
for path in errors_404:
    print(f"404: {path}")

print("\n=== 302 REDIRECTS ===")
for path in errors_302:
    print(f"302: {path}")

print("\n=== OTHER STATUS CODES ===")
for path, code in other_codes:
    print(f"{code}: {path}")

print("\n=== SUMMARY ===")
print(f"Total 404 errors: {len(errors_404)}")
print(f"Total 302 redirects: {len(errors_302)}")
print(f"Total 200 success: {len(success_200)}")
print(f"Total other codes: {len(other_codes)}")