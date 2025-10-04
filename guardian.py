"""Guardian Protection System Wrapper
Provides enterprise-grade protection capabilities for the TOP 0.1% application
"""

"""Compatibility shim for guardian module."""

try:
    import app.guardian as _g

    Guardian = getattr(_g, "Guardian", None)
    protect_transaction = getattr(_g, "protect_transaction", None)

    __all__ = ["Guardian", "protect_transaction"]
except Exception:  # pragma: no cover - optional module
    __all__ = []
