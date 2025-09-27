# ruff: noqa: E402
import sys
import types

from fastapi import APIRouter

# Create shim module for app.auth
auth_mod = types.ModuleType("app.auth")
auth_router = APIRouter()


def _shim():
    return {"ok": True}


auth_router.add_api_route("/__shim_ping", _shim, methods=["GET"])
# Assign router via setattr so static analyzers don't flag missing attributes on the module object
setattr(auth_mod, "router", auth_router)  # type: ignore[attr-defined]

# Ensure the shim is available under both 'app.auth' and 'app' package attr
sys.modules["app.auth"] = auth_mod

import app as apppkg

print("app.auth attr (package):", getattr(apppkg, "auth", None))
print("type:", type(getattr(apppkg, "auth", None)))
print("has router:", hasattr(getattr(apppkg, "auth", None), "router"))

print("app.auth attr:", apppkg.auth)
print("type:", type(apppkg.auth))
print("has router:", hasattr(apppkg.auth, "router"))
print("apppkg auth router:", getattr(apppkg.auth, "router", None))
