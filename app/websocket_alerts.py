"""
Real - time WebSocket Alerts Module for Klerno Labs.

Provides WebSocket - based real - time alerts for Professional and Enterprise tiers.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

logger = logging.getLogger(__name__)


class AlertType(str, Enum):
    """Types of real - time alerts."""

    RISK_ALERT = "risk_alert"
    TRANSACTION_ALERT = "transaction_alert"
    COMPLIANCE_ALERT = "compliance_alert"
    SYSTEM_ALERT = "system_alert"
    THRESHOLD_ALERT = "threshold_alert"


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class WebSocketAlert:
    """Real - time alert structure."""

    id: str
    type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    data: dict[str, Any]
    timestamp: datetime
    user_id: str | None = None
    expires_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert alert to dictionary for JSON serialization."""
        result = asdict(self)
        result["timestamp"] = self.timestamp.isoformat()
        if self.expires_at:
            result["expires_at"] = self.expires_at.isoformat()
        return result


class WebSocketManager:
    """Manages WebSocket connections and real - time alerts."""

    def __init__(self):
        # Active connections by user ID
        self.connections: dict[str, set[WebSocket]] = {}
        # Connection metadata
        self.connection_info: dict[WebSocket, dict[str, Any]] = {}
        # Alert queue for offline users
        self.pending_alerts: dict[str, list[WebSocketAlert]] = {}
        # Connection lock for thread safety
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: str, tier: str = "starter"):
        """Connect a WebSocket client."""
        await websocket.accept()

        async with self._lock:
            if user_id not in self.connections:
                self.connections[user_id] = set()

            self.connections[user_id].add(websocket)
            self.connection_info[websocket] = {
                "user_id": user_id,
                "tier": tier,
                "connected_at": datetime.now(UTC),
                "last_ping": datetime.now(UTC),
            }

        logger.info(f"WebSocket connected for user {user_id} (tier: {tier})")

        # Send any pending alerts
        await self._send_pending_alerts(user_id, websocket)

        # Send connection confirmation
        await self._send_to_websocket(
            websocket,
            {
                "type": "connection_established",
                "message": "Real - time alerts active",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    async def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket client."""
        async with self._lock:
            if websocket in self.connection_info:
                user_id = self.connection_info[websocket]["user_id"]

                # Remove from connections
                if user_id in self.connections:
                    self.connections[user_id].discard(websocket)
                    if not self.connections[user_id]:
                        del self.connections[user_id]

                # Remove connection info
                del self.connection_info[websocket]

                logger.info(f"WebSocket disconnected for user {user_id}")

    async def send_alert(self, alert: WebSocketAlert):
        """Send alert to specific user or broadcast."""
        if alert.user_id:
            await self._send_to_user(alert.user_id, alert)
        else:
            await self._broadcast_alert(alert)

    async def send_risk_alert(
        self,
        user_id: str,
        transaction_data: dict[str, Any],
        risk_score: float,
        risk_level: str,
        recommendations: list[str],
    ):
        """Send risk - based alert."""
        severity = self._get_severity_from_risk(risk_level)

        alert = WebSocketAlert(
            id=f"risk_{int(time.time())}_{user_id}",
            type=AlertType.RISK_ALERT,
            severity=severity,
            title=f"{risk_level} Risk Transaction Detected",
            message=(
                f"Transaction with risk score {risk_score:.2f} " f"requires attention"
            ),
            data={
                "transaction": transaction_data,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "recommendations": recommendations,
            },
            timestamp=datetime.now(UTC),
            user_id=user_id,
        )

        await self.send_alert(alert)

    async def send_compliance_alert(
        self,
        user_id: str,
        compliance_issue: str,
        transaction_data: dict[str, Any],
        severity: AlertSeverity = AlertSeverity.WARNING,
    ):
        """Send compliance - related alert."""
        alert = WebSocketAlert(
            id=f"compliance_{int(time.time())}_{user_id}",
            type=AlertType.COMPLIANCE_ALERT,
            severity=severity,
            title="Compliance Alert",
            message=f"Compliance issue detected: {compliance_issue}",
            data={"issue": compliance_issue, "transaction": transaction_data},
            timestamp=datetime.now(UTC),
            user_id=user_id,
        )

        await self.send_alert(alert)

    async def send_threshold_alert(
        self,
        user_id: str,
        threshold_type: str,
        current_value: float,
        threshold_value: float,
        severity: AlertSeverity = AlertSeverity.WARNING,
    ):
        """Send threshold - based alert."""
        alert = WebSocketAlert(
            id=f"threshold_{int(time.time())}_{user_id}",
            type=AlertType.THRESHOLD_ALERT,
            severity=severity,
            title=f"{threshold_type} Threshold Exceeded",
            message=(
                f"{threshold_type} has reached {current_value}, "
                f"exceeding threshold of {threshold_value}"
            ),
            data={
                "threshold_type": threshold_type,
                "current_value": current_value,
                "threshold_value": threshold_value,
                "percentage": (current_value / threshold_value) * 100,
            },
            timestamp=datetime.now(UTC),
            user_id=user_id,
        )

        await self.send_alert(alert)

    async def broadcast_system_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.INFO,
        data: dict[str, Any] = None,
    ):
        """Broadcast system - wide alert."""
        alert = WebSocketAlert(
            id=f"system_{int(time.time())}",
            type=AlertType.SYSTEM_ALERT,
            severity=severity,
            title=title,
            message=message,
            data=data or {},
            timestamp=datetime.now(UTC),
        )

        await self._broadcast_alert(alert)

    async def _send_to_user(self, user_id: str, alert: WebSocketAlert):
        """Send alert to specific user."""
        async with self._lock:
            if user_id in self.connections:
                # Send to all user's connections
                dead_connections = set()
                for websocket in self.connections[user_id].copy():
                    if not await self._send_to_websocket(websocket, alert.to_dict()):
                        dead_connections.add(websocket)

                # Clean up dead connections
                for dead_ws in dead_connections:
                    await self.disconnect(dead_ws)
            else:
                # User not connected, store alert for later
                if user_id not in self.pending_alerts:
                    self.pending_alerts[user_id] = []
                self.pending_alerts[user_id].append(alert)

                # Limit pending alerts to prevent memory issues
                if len(self.pending_alerts[user_id]) > 50:
                    self.pending_alerts[user_id] = self.pending_alerts[user_id][-50:]

    async def _broadcast_alert(self, alert: WebSocketAlert):
        """Broadcast alert to all connected users."""
        async with self._lock:
            dead_connections = set()

            for _user_id, websockets in self.connections.items():
                for websocket in websockets.copy():
                    # Check if user has appropriate tier for alert
                    if self._should_receive_alert(websocket, alert):
                        if not await self._send_to_websocket(
                            websocket, alert.to_dict()
                        ):
                            dead_connections.add(websocket)

            # Clean up dead connections
            for dead_ws in dead_connections:
                await self.disconnect(dead_ws)

    async def _send_to_websocket(
        self, websocket: WebSocket, data: dict[str, Any]
    ) -> bool:
        """Send data to specific WebSocket. Returns True if successful."""
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json(data)
                return True
        except (WebSocketDisconnect, ConnectionResetError, RuntimeError) as e:
            logger.warning(f"Failed to send WebSocket message: {e}")

        return False

    async def _send_pending_alerts(self, user_id: str, websocket: WebSocket):
        """Send pending alerts to newly connected user."""
        if user_id in self.pending_alerts:
            alerts = self.pending_alerts[user_id]
            for alert in alerts:
                await self._send_to_websocket(websocket, alert.to_dict())

            # Clear pending alerts
            del self.pending_alerts[user_id]

    def _should_receive_alert(
        self, websocket: WebSocket, alert: WebSocketAlert
    ) -> bool:
        """Check if user should receive this alert based on tier."""
        if websocket not in self.connection_info:
            return False

        user_tier = self.connection_info[websocket].get("tier", "starter").lower()

        # Professional and Enterprise get all alerts
        if user_tier in ["professional", "enterprise"]:
            return True

        # Starter only gets basic alerts
        return bool(
            alert.type in [AlertType.SYSTEM_ALERT]
            and alert.severity in [AlertSeverity.INFO, AlertSeverity.WARNING]
        )

    def _get_severity_from_risk(self, risk_level: str) -> AlertSeverity:
        """Convert risk level to alert severity."""
        mapping = {
            "LOW": AlertSeverity.INFO,
            "MEDIUM": AlertSeverity.WARNING,
            "HIGH": AlertSeverity.HIGH,
            "CRITICAL": AlertSeverity.CRITICAL,
        }
        return mapping.get(risk_level.upper(), AlertSeverity.INFO)

    async def get_connection_stats(self) -> dict[str, Any]:
        """Get WebSocket connection statistics."""
        async with self._lock:
            total_connections = sum(
                len(websockets) for websockets in self.connections.values()
            )
            unique_users = len(self.connections)
            pending_alerts_count = sum(
                len(alerts) for alerts in self.pending_alerts.values()
            )

            tier_stats = {}
            for websockets in self.connections.values():
                for ws in websockets:
                    if ws in self.connection_info:
                        tier = self.connection_info[ws].get("tier", "unknown")
                        tier_stats[tier] = tier_stats.get(tier, 0) + 1

            return {
                "total_connections": total_connections,
                "unique_users": unique_users,
                "pending_alerts": pending_alerts_count,
                "tier_distribution": tier_stats,
                "timestamp": datetime.now(UTC).isoformat(),
            }


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


async def handle_websocket_connection(
    websocket: WebSocket, user_id: str, tier: str = "starter"
):
    """Handle WebSocket connection lifecycle."""
    try:
        await websocket_manager.connect(websocket, user_id, tier)

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for ping or other messages
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)

                # Handle ping / pong for connection health
                if data.get("type") == "ping":
                    await websocket.send_json(
                        {"type": "pong", "timestamp": datetime.now(UTC).isoformat()}
                    )

                    # Update last ping time
                    if websocket in websocket_manager.connection_info:
                        websocket_manager.connection_info[websocket]["last_ping"] = (
                            datetime.now(UTC)
                        )

            except TimeoutError:
                # Send keep - alive ping
                await websocket.send_json(
                    {"type": "keep_alive", "timestamp": datetime.now(UTC).isoformat()}
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        await websocket_manager.disconnect(websocket)


# Utility functions for easy integration


async def send_risk_alert(
    user_id: str,
    transaction_data: dict[str, Any],
    risk_score: float,
    risk_level: str,
    recommendations: list[str],
):
    """Send risk alert to user."""
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
    """Send compliance alert to user."""
    await websocket_manager.send_compliance_alert(
        user_id,
        compliance_issue,
        transaction_data,
        severity,
    )


async def send_threshold_alert(
    user_id: str,
    threshold_type: str,
    current_value: float,
    threshold_value: float,
    severity: AlertSeverity = AlertSeverity.WARNING,
):
    """Send threshold alert to user."""
    await websocket_manager.send_threshold_alert(
        user_id,
        threshold_type,
        current_value,
        threshold_value,
        severity,
    )


async def broadcast_system_alert(
    title: str,
    message: str,
    severity: AlertSeverity = AlertSeverity.INFO,
    data: dict[str, Any] = None,
):
    """Broadcast system alert to all users."""
    await websocket_manager.broadcast_system_alert(
        title,
        message,
        severity,
        data,
    )


def is_websocket_feature_available(user_tier: str) -> bool:
    """Check if user has access to real - time WebSocket alerts."""
    return user_tier.lower() in ["professional", "enterprise"]
