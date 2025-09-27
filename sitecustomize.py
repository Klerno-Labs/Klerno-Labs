"""Site customization loaded at interpreter start for test runs.

This module attempts to import `app.auth` early and inject the
compatibility helpers `create_access_token` and `verify_token` into
builtins so older tests that call these names without importing them
continue to work during the migration.
"""

try:
    import builtins

    from app import auth as _auth

    if hasattr(_auth, "create_access_token") and not hasattr(
        builtins, "create_access_token"
    ):
        setattr(builtins, "create_access_token", _auth.create_access_token)  # type: ignore[attr-defined]
    if hasattr(_auth, "verify_token") and not hasattr(builtins, "verify_token"):
        setattr(builtins, "verify_token", _auth.verify_token)  # type: ignore[attr-defined]
except Exception:
    # Best-effort: tests will still fail later if auth cannot be imported.
    pass
