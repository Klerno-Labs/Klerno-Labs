"""Test specific routes to debug elite.css issue."""

import importlib
import sys

from fastapi.testclient import TestClient

# Import the enterprise app
sys.path.insert(0, ".")
enterprise_module = importlib.import_module("enterprise_main_v2")
app = enterprise_module.app
client = TestClient(app)

# Test just the elite.css routes
css_paths = ["/css/elite.css", "/static/css/elite.css"]

for path in css_paths:
    try:
        response = client.get(path)
        print(
            f'{path}: {response.status_code} - {response.headers.get("content-type")}'
        )
        if response.status_code == 404:
            print(f"  Content: {response.text[:200]}")
    except Exception as e:
        print(f"{path}: ERROR - {e}")

# Also test direct file access
from pathlib import Path

print("\nDirect file check:")
css_path = Path("static/css/elite-enhancements.css")
print(f"elite-enhancements.css exists: {css_path.exists()}")
if css_path.exists():
    print(f"File size: {css_path.stat().st_size} bytes")
