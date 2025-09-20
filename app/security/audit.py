"""
Comprehensive Audit Logging System
Tracks all security-relevant events for compliance and monitoring
"""

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any


class AuditEventType(Enum):
    """Types of audit events"""

    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    PERMISSION_GRANT = "permission_grant"
    PERMISSION_REVOKE = "permission_revoke"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    ADMIN_ACTION = "admin_action"
    SECURITY_VIOLATION = "security_violation"
    API_ACCESS = "api_access"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


class AuditLogger:
    """Comprehensive audit logging system"""

    def __init__(self, log_file: str = "audit.log"):
        self.log_file = log_file
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Setup audit logger with proper formatting"""
        logger = logging.getLogger("audit")
        logger.setLevel(logging.INFO)

        # Remove existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # File handler for audit logs
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.INFO)

        # JSON formatter for structured logging
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": %(message)s}'
        )
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        return logger

    def log_event(
        self,
        event_type: AuditEventType,
        user_id: str | None = None,
        ip_address: str | None = None,
        details: dict[str, Any] | None = None,
        success: bool = True,
    ):
        """Log an audit event"""

        event_data = {
            "event_type": event_type.value,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "ip_address": ip_address,
            "success": success,
            "details": details or {},
        }

        self.logger.info(json.dumps(event_data))

    def log_login(
        self, user_id: str, ip_address: str, success: bool, method: str = "password"
    ):
        """Log login attempt"""
        event_type = (
            AuditEventType.LOGIN_SUCCESS if success else AuditEventType.LOGIN_FAILURE
        )
        self.log_event(
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            details={"auth_method": method},
            success=success,
        )

    def log_data_access(
        self, user_id: str, resource: str, action: str, ip_address: str | None = None
    ):
        """Log data access event"""
        self.log_event(
            event_type=AuditEventType.DATA_ACCESS,
            user_id=user_id,
            ip_address=ip_address,
            details={"resource": resource, "action": action},
        )

    def log_admin_action(
        self, admin_id: str, action: str, target: str, ip_address: str | None = None
    ):
        """Log administrative action"""
        self.log_event(
            event_type=AuditEventType.ADMIN_ACTION,
            user_id=admin_id,
            ip_address=ip_address,
            details={"action": action, "target": target},
        )

    def log_security_violation(
        self,
        event_details: dict[str, Any],
        ip_address: str | None = None,
        user_id: str | None = None,
    ):
        """Log security violation"""
        self.log_event(
            event_type=AuditEventType.SECURITY_VIOLATION,
            user_id=user_id,
            ip_address=ip_address,
            details=event_details,
            success=False,
        )


# Global audit logger instance
audit_logger = AuditLogger()


def audit_decorator(event_type: AuditEventType):
    """Decorator to automatically audit function calls"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                audit_logger.log_event(
                    event_type=event_type,
                    details={"function": func.__name__},
                    success=True,
                )
                return result
            except Exception as e:
                audit_logger.log_event(
                    event_type=event_type,
                    details={"function": func.__name__, "error": str(e)},
                    success=False,
                )
                raise

        return wrapper

    return decorator
