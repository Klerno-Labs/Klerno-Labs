import sys

sys.path.insert(0, ".")
from importlib import import_module

app_mod = import_module("app.main")
app = app_mod.app
found = [r for r in app.routes if getattr(r, "path", None) == "/auth/login_api"]
print("found_count=", len(found))
for r in found:
    print("route:", r.path, type(r), getattr(r, "methods", None))

# Also print any similar paths
candidates = [r for r in app.routes if "/auth/login" in (r.path or "")]
print("auth-related routes:")
for r in candidates:
    print("-", r.path)
