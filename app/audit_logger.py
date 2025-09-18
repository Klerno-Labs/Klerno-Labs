# app / audit_logger.py
"""
Comprehensive audit logging system for security events and compliance.
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Union

from fastapi import Request
from pydantic import BaseModel, Field


class AuditEventType(str, Enum):
    """Types of audit events to track."""
    # Authentication events
    LOGIN_SUCCESS="auth.login.success"
    LOGIN_FAILURE="auth.login.failure"
    LOGOUT="auth.logout"
    SESSION_EXPIRED="auth.session.expired"
    PASSWORD_CHANGE="auth.password.change"

    # API access events
    API_ACCESS="api.access"
    API_ACCESS_DENIED="api.access.denied"
    API_KEY_ROTATION="api.key.rotation"

    # Data access events
    DATA_EXPORT="data.export"
    DATA_IMPORT="data.import"
    TRANSACTION_ANALYSIS="data.transaction.analysis"

    # Administrative events
    ADMIN_ACCESS="admin.access"
    USER_CREATED="admin.user.created"
    USER_UPDATED="admin.user.updated"
    USER_DELETED="admin.user.deleted"
    SETTINGS_CHANGED="admin.settings.changed"

    # Security events
    CSRF_VIOLATION="security.csrf.violation"
    RATE_LIMIT_EXCEEDED="security.rate_limit.exceeded"
    SUSPICIOUS_ACTIVITY="security.suspicious.activity"

    # System events
    SYSTEM_START="system.start"
    SYSTEM_SHUTDOWN="system.shutdown"
    ERROR="system.error"


class AuditEvent(BaseModel):
    """Structured audit event model."""
    timestamp: datetime=Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: AuditEventType
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    user_role: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    outcome: str="success"  # success, failure, error
    details: Dict[str, Any] = Field(default_factory=dict)
    risk_score: Optional[float] = None


class AuditLogger:
    """
    Centralized audit logging system with structured logging and security focus.
    """


    def __init__(self):
        self.logger=self._setup_logger()


    def _setup_logger(self) -> logging.Logger:
        """Configure audit logger with proper formatting and handlers."""
        logger=logging.getLogger("klerno.audit")
        logger.setLevel(logging.INFO)

        # Prevent duplicate handlers
        if logger.handlers:
            return logger

        # Create logs directory
        log_dir=Path("logs")
        log_dir.mkdir(exist_ok=True)

        # JSON formatter for structured logging


        class JSONFormatter(logging.Formatter):


            def format(self, record):
                log_entry={
                    "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
                        "level": record.levelname,
                        "logger": record.name,
                        "message": record.getMessage(),
                        }

                # Add audit event data if present
                if hasattr(record, "audit_event"):
                    log_entry["audit_event"] = record.audit_event

                return json.dumps(log_entry, default=str)

        # File handler for audit logs
        file_handler=logging.FileHandler(log_dir / "audit.log")
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)

        # Console handler for development
        if os.getenv("APP_ENV", "dev").lower() == "dev":
            console_handler=logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(
                "%(asctime)s - AUDIT - %(message)s"
            ))
            logger.addHandler(console_handler)

        return logger


    def log_event(self, event: AuditEvent) -> None:
        """Log an audit event."""
        self.logger.info(
            f"{event.event_type.value} - {event.outcome}",
                extra={"audit_event": event.model_dump()}
        )


    def log_auth_success(
        self,
            user_id: str,
            user_email: str,
            user_role: str,
            request: Optional[Request] = None
    ) -> None:
        """Log successful authentication."""
        event=AuditEvent(
            event_type=AuditEventType.LOGIN_SUCCESS,
                user_id=user_id,
                user_email=user_email,
                user_role=user_role,
                outcome="success"
        )

        if request:
            self._enrich_from_request(event, request)

        self.log_event(event)


    def log_auth_failure(
        self,
            email: str,
            reason: str,
            request: Optional[Request] = None
    ) -> None:
        """Log failed authentication attempt."""
        event=AuditEvent(
            event_type=AuditEventType.LOGIN_FAILURE,
                user_email=email,
                outcome="failure",
                details={"reason": reason}
        )

        if request:
            self._enrich_from_request(event, request)

        self.log_event(event)


    def log_api_access(
        self,
            endpoint: str,
            method: str,
            user_id: Optional[str] = None,
            api_key_used: bool=False,
            request: Optional[Request] = None
    ) -> None:
        """Log API access."""
        event=AuditEvent(
            event_type=AuditEventType.API_ACCESS,
                user_id=user_id,
                resource=endpoint,
                action=method,
                outcome="success",
                details={"api_key_used": api_key_used}
        )

        if request:
            self._enrich_from_request(event, request)

        self.log_event(event)


    def log_data_export(
        self,
            export_type: str,
            record_count: int,
            user_id: str,
            request: Optional[Request] = None
    ) -> None:
        """Log data export operations."""
        event=AuditEvent(
            event_type=AuditEventType.DATA_EXPORT,
                user_id=user_id,
                action="export",
                outcome="success",
                details={
                "export_type": export_type,
                    "record_count": record_count
            }
        )

        if request:
            self._enrich_from_request(event, request)

        self.log_event(event)


    def log_admin_action(
        self,
            action: str,
            target: str,
            user_id: str,
            details: Optional[Dict[str, Any]] = None,
            request: Optional[Request] = None
    ) -> None:
        """Log administrative actions."""
        event=AuditEvent(
            event_type=AuditEventType.ADMIN_ACCESS,
                user_id=user_id,
                action=action,
                resource=target,
                outcome="success",
                details=details or {}
        )

        if request:
            self._enrich_from_request(event, request)

        self.log_event(event)


    def log_security_event(
        self,
            event_type: AuditEventType,
            details: Dict[str, Any],
            request: Optional[Request] = None,
            risk_score: Optional[float] = None
    ) -> None:
        """Log security - related events."""
        event=AuditEvent(
            event_type=event_type,
                outcome="security_event",
                details=details,
                risk_score=risk_score
        )

        if request:
            self._enrich_from_request(event, request)

        self.log_event(event)


    def _enrich_from_request(self, event: AuditEvent, request: Request) -> None:
        """Enrich audit event with request information."""
        event.ip_address=self._get_client_ip(request)
        event.user_agent=request.headers.get("user - agent")
        event.request_id=getattr(request.state, "request_id", None)
        event.session_id=request.cookies.get("session")


    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request, handling proxies."""
        # Check for forwarded headers (proxy / load balancer)
        forwarded_for=request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()

        real_ip=request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fallback to direct client IP
        if request.client:
            return request.client.host

        return "unknown"


# Global audit logger instance
audit_logger=AuditLogger()


def log_auth_success(user_id: str, user_email: str, user_role: str, request: Optional[Request] = None):
    """Convenience function for logging successful authentication."""
    audit_logger.log_auth_success(user_id, user_email, user_role, request)


def log_auth_failure(email: str, reason: str, request: Optional[Request] = None):
    """Convenience function for logging failed authentication."""
    audit_logger.log_auth_failure(email, reason, request)


def log_api_access(endpoint: str, method: str, user_id: Optional[str] = None, api_key_used: bool = False, request: Optional[Request] = None):
    """Convenience function for logging API access."""
    audit_logger.log_api_access(endpoint, method, user_id, api_key_used, request)


def log_security_event(event_type: AuditEventType, details: Dict[str, Any], request: Optional[Request] = None, risk_score: Optional[float] = None):
    """Convenience function for logging security events."""
    audit_logger.log_security_event(event_type, details, request, risk_score)
