"""AI Processor Module for Enterprise Integration
Provides access to AI processing functionality.
"""

"""Compatibility shim for app.ai.processor."""

try:
    import app.ai.processor as _ap

    AIProcessor = getattr(_ap, "AIProcessor", None)
    process_transaction = getattr(_ap, "process_transaction", None)
    analyze_risk = getattr(_ap, "analyze_risk", None)

    __all__ = ["AIProcessor", "analyze_risk", "process_transaction"]
except Exception:  # pragma: no cover - optional module
    __all__ = []
