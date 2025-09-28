"""Site customization loaded at interpreter start for test runs.

This module attempts to import `app.auth` early and inject the
compatibility helpers `create_access_token` and `verify_token` into
builtins so older tests that call these names without importing them
continue to work during the migration.
"""

try:
    import builtins
    from types import ModuleType
    from typing import cast

    from app import auth as _auth

    builtins_mod = cast(ModuleType, builtins)
    if hasattr(_auth, "create_access_token") and not hasattr(
        builtins_mod, "create_access_token"
    ):
        builtins_mod.create_access_token = _auth.create_access_token
    if hasattr(_auth, "verify_token") and not hasattr(builtins_mod, "verify_token"):
        builtins_mod.verify_token = _auth.verify_token
except Exception:
    # Best-effort: tests will still fail later if auth cannot be imported.
    pass
