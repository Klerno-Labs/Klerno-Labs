"""
Enterprise Monitoring System Wrapper
Provides enterprise-grade monitoring capabilities for the TOP 0.1% application
"""

"""Compatibility shim for enterprise monitoring.

This file re-exports the public API from `app.enterprise_monitoring` when
available. Using explicit imports avoids star-import issues with linters.
"""

try:
    import app.enterprise_monitoring as _em  # type: ignore

    get_monitoring_client = getattr(_em, "get_monitoring_client", None)
    record_metric = getattr(_em, "record_metric", None)
    MonitoringClient = getattr(_em, "MonitoringClient", None)

    __all__ = ["get_monitoring_client", "record_metric", "MonitoringClient"]
except Exception:  # pragma: no cover - optional enterprise module
    __all__ = []
