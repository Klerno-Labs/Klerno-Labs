import importlib
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, ".")

m = importlib.import_module("enterprise_main_v2")
app = getattr(m, "app")
client = TestClient(app)

paths = [
    "/",
    "/signup",
    "/login",
    "/auth/login",
    "/auth/signup",
    "/admin/",
    "/static/js/main.js",
    "/js/main.js",
    "/static/images/hero-bg.jpg",
    "/images/hero-bg.jpg",
    "/offline.html",
]

results = {}
for p in paths:
    r = client.get(p)
    results[p] = (r.status_code, r.headers.get("content-type"))

for p, (s, t) in results.items():
    print(f"{p}: {s} - {t}")
