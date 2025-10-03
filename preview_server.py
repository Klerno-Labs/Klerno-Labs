"""Local preview helper that provides lightweight shims for missing
`app.auth` during local preview so the full `enterprise_main_v2` app
can start without modifying production code.

This file inserts a small module into `sys.modules['app.auth']` exposing
an `APIRouter` at `router` so `enterprise_main_v2` can include it.
"""

from __future__ import annotations

import sys
import types

from fastapi import APIRouter

# Create a small shim module for `app.auth` with a minimal router so
# enterprise_main_v2 can call `app.include_router(auth.router, ...)`
mod = types.ModuleType("app.auth")
router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/__shim_ping")
def _shim_ping():
    return {"ok": True, "shim": True}


mod.router = router

# Register shim before importing the package that expects it
import contextlib

sys.modules["app.auth"] = mod
pkg = sys.modules.get("app")
if pkg is not None:
    with contextlib.suppress(Exception):
        pkg.auth = mod

# Now import the real app entrypoint
import enterprise_main_v2 as _enterprise

# Expose the FastAPI app object for uvicorn: preview_server:app
app = _enterprise.app
# ruff: noqa: E402
