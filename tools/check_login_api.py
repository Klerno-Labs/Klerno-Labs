import sys

sys.path.insert(0, ".")
from importlib import import_module

app_mod = import_module("app.main")
app = app_mod.app
found = [r for r in app.routes if getattr(r, "path", None) == "/auth/login_api"]
for _r in found:
    pass

# Also print any similar paths
candidates = [r for r in app.routes if "/auth/login" in (r.path or "")]
for _r in candidates:
    pass
