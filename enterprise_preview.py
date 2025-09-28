r"""Robust launcher for previewing the enterprise app locally.

This module performs the following safely:
1. Creates a lightweight `app.auth` shim module exposing `router`.
2. Ensures the `app` package attribute `auth` points at the shim so
   package-level references resolve correctly.
3. Imports `enterprise_main_v2` and exposes `app` for uvicorn.

Run with:
  & ".\.venv-py311\Scripts\python.exe" -m uvicorn enterprise_preview:app --host 127.0.0.1 --port 8002 --reload
"""

from __future__ import annotations

import sys
import types

from fastapi import APIRouter


def _ensure_auth_shim() -> None:
    """Create and register a minimal `app.auth` shim if the real module
    is not importable. This ensures `enterprise_main_v2`'s import-time
    references to `app.auth` will resolve to an object with `.router`.
    """
    try:
        # If real module import succeeds, prefer it
        import importlib

        importlib.import_module("app.auth")
        return
    except Exception:
        pass

    # Build shim module
    mod = types.ModuleType("app.auth")
    router = APIRouter(prefix="/auth", tags=["auth"])

    @router.get("/__shim_ping")
    def _shim_ping():
        return {"ok": True, "shim": True}

    setattr(mod, "router", router)

    # Register both the module import and set in the already-imported
    # `app` package if it's present in sys.modules so attribute access
    # like `app.auth` resolves to the shim.
    sys.modules["app.auth"] = mod

    pkg = sys.modules.get("app")
    if pkg is not None:
        import contextlib

        with contextlib.suppress(Exception):
            setattr(pkg, "auth", mod)


# Ensure shim exists before importing enterprise_main_v2
_ensure_auth_shim()

import enterprise_main_v2 as _enterprise  # noqa: E402

# Expose the app object for uvicorn
app = _enterprise.app
