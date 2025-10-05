"""Enterprise Security System Wrapper
Provides enterprise-grade security capabilities for the TOP 0.1% application.
"""

"""Compatibility shim for enterprise security.

Re-export a small, explicit API when `app.enterprise_security` is available.
"""

try:
    import app.enterprise_security as _es

    HardenedSecurity = getattr(_es, "HardenedSecurity", None)
    enable_hardening = getattr(_es, "enable_hardening", None)

    __all__ = ["HardenedSecurity", "enable_hardening"]
except Exception:  # pragma: no cover - optional enterprise module
    __all__ = []
