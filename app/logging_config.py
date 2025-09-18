"""
Structured logging configuration for Klerno Labs.
Provides consistent, structured logging throughout the application.
"""

import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict

import structlog
from pythonjsonlogger.json import JsonFormatter

from app.settings import get_settings


def configure_logging() -> None:
    """Configure structured logging for the application."""
    settings=get_settings()

    # Configure standard library logging
    log_level=getattr(logging, settings.app_env.upper() if settings.app_env != "dev" else "DEBUG")

    # Remove existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # JSON formatter for structured logs
    json_formatter=JsonFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    console_handler=logging.StreamHandler(sys.stdout)

    if settings.app_env == "production":
        console_handler.setFormatter(json_formatter)
    else:
        # Human - readable format for development
        formatter=logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%H:%M:%S"
        )
        console_handler.setFormatter(formatter)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
            handlers=[console_handler],
            force=True
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.processors.add_logger_name,
                structlog.processors.add_log_level,
                structlog.processors.StackInfoRenderer(),
                structlog.dev.set_exc_info,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.dev.ConsoleRenderer() if settings.app_env == "dev"
            else structlog.processors.JSONRenderer()
        ],
            wrapper_class=structlog.make_filtering_bound_logger(log_level),
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
            )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger for a specific module."""
    return structlog.get_logger(name)


class LoggingMixin:
    """Mixin to add structured logging to classes."""

    @property


    def logger(self) -> structlog.BoundLogger:
        """Get logger for this class."""
        return get_logger(self.__class__.__name__)


def log_request_response(
    method: str,
        url: str,
        status_code: int,
        duration: float,
        request_id: str=None,
        user_id: str=None,
        **kwargs
) -> None:
    """Log HTTP request / response details."""
    logger=get_logger("http")

    log_data={
        "method": method,
            "url": url,
            "status_code": status_code,
            "duration_ms": round(duration * 1000, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    if request_id:
        log_data["request_id"] = request_id

    if user_id:
        log_data["user_id"] = user_id

    log_data.update(kwargs)

    if status_code >= 500:
        logger.error("HTTP request failed", **log_data)
    elif status_code >= 400:
        logger.warning("HTTP request error", **log_data)
    else:
        logger.info("HTTP request", **log_data)


def log_security_event(
    event_type: str,
        user_id: str=None,
        ip_address: str=None,
        details: Dict[str, Any] = None,
        **kwargs
) -> None:
    """Log security - related events."""
    logger=get_logger("security")

    log_data={
        "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    if user_id:
        log_data["user_id"] = user_id

    if ip_address:
        log_data["ip_address"] = ip_address

    if details:
        log_data["details"] = details

    log_data.update(kwargs)

    # Security events are always important
    if event_type in ["authentication_failure", "authorization_failure", "suspicious_activity"]:
        logger.warning("Security event", **log_data)
    else:
        logger.info("Security event", **log_data)


def log_business_event(
    event_type: str,
        entity_type: str=None,
        entity_id: str=None,
        user_id: str=None,
        details: Dict[str, Any] = None,
        **kwargs
) -> None:
    """Log business logic events."""
    logger=get_logger("business")

    log_data={
        "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    if entity_type:
        log_data["entity_type"] = entity_type

    if entity_id:
        log_data["entity_id"] = entity_id

    if user_id:
        log_data["user_id"] = user_id

    if details:
        log_data["details"] = details

    log_data.update(kwargs)

    logger.info("Business event", **log_data)


def log_performance_metric(
    operation: str,
        duration: float,
        success: bool=True,
        details: Dict[str, Any] = None,
        **kwargs
) -> None:
    """Log performance metrics."""
    logger=get_logger("performance")

    log_data={
        "operation": operation,
            "duration_ms": round(duration * 1000, 2),
            "success": success,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    if details:
        log_data["details"] = details

    log_data.update(kwargs)

    if not success or duration > 5.0:  # Log slow operations as warnings
        logger.warning("Performance metric", **log_data)
    else:
        logger.info("Performance metric", **log_data)


# Initialize logging when module is imported
if __name__ != "__main__":
    try:
        configure_logging()
    except Exception:
        # Fallback to basic logging if configuration fails
        logging.basicConfig(level=logging.INFO)
