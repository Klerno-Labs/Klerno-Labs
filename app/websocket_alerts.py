




"""Compatibility shim for removed websocket_alerts module.

This module provided enterprise-only WebSocket alerting. To avoid
raising on import during consolidation, provide a lightweight no-op shim
that preserves the public functions and types. Callers can continue to
import the names; calls will be logged but won't raise.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class _NoopWebsocketManager:
    """Minimal async stub that logs calls instead of sending real WS
    messages.
    """

    async def send_risk_alert(
        self,
        user_id: str,
        transaction_data: dict[str, Any],
        risk_score: float,
        risk_level: str,
        recommendations: list[str],
    ):
        logger.debug(
            "websocket_alerts.send_risk_alert (noop) user=%s score=%s "
            "level=%s",
            user_id,
            risk_score,
            risk_level,
        )

    async def send_compliance_alert(
        self,
        user_id: str,
        compliance_issue: str,
        transaction_data: dict[str, Any],
        severity: AlertSeverity = AlertSeverity.WARNING,
    ):
        logger.debug(
            "websocket_alerts.send_compliance_alert (noop) user=%s "
            "issue=%s severity=%s",
            user_id,
            compliance_issue,
            severity,
        )

    async def send_threshold_alert(
        self,
        user_id: str,
        threshold_type: str,
        current_value: float,
        threshold_value: float,
        severity: AlertSeverity = AlertSeverity.WARNING,
    ):
        logger.debug(
            "websocket_alerts.send_threshold_alert (noop) user=%s "
            "type=%s current=%s threshold=%s severity=%s",
            user_id,
            threshold_type,
            current_value,
            threshold_value,
            severity,
        )

    async def broadcast_system_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.INFO,
        data: dict[str, Any] | None = None,
    ):
        logger.debug(
            "websocket_alerts.broadcast_system_alert (noop) "
            "title=%s severity=%s",
            title,
            severity,
        )


# single instance used by the shimmed functions
websocket_manager = _NoopWebsocketManager()


async def send_risk_alert(
    user_id: str,
    transaction_data: dict[str, Any],
    risk_score: float,
    risk_level: str,
    recommendations: list[str],
):
    """Send risk alert to user (noop shim)."""
    await websocket_manager.send_risk_alert(
        user_id,
        transaction_data,
        risk_score,
        risk_level,
        recommendations,
    )


async def send_compliance_alert(
    user_id: str,
    compliance_issue: str,
    transaction_data: dict[str, Any],
    severity: AlertSeverity = AlertSeverity.WARNING,
):
    """Send compliance alert to user (noop shim)."""
    await websocket_manager.send_compliance_alert(
        user_id, compliance_issue, transaction_data, severity
    )


async def send_threshold_alert(
    user_id: str,
    threshold_type: str,
    current_value: float,
    threshold_value: float,
    severity: AlertSeverity = AlertSeverity.WARNING,
):
    """Send threshold alert to user (noop shim)."""
    await websocket_manager.send_threshold_alert(
        user_id, threshold_type, current_value, threshold_value, severity
    )


async def broadcast_system_alert(
    title: str,
    message: str,
    severity: AlertSeverity = AlertSeverity.INFO,
    data: dict[str, Any] | None = None,
):
    """Broadcast system alert to all users (noop shim)."""
    await websocket_manager.broadcast_system_alert(
        title, message, severity, data
    )


def is_websocket_feature_available(user_tier: str) -> bool:
    """Check if user has access to real-time WebSocket alerts."""
    try:
        return user_tier.lower() in ["professional", "enterprise"]
    except Exception:
        return False
