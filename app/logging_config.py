"""Structured logging configuration for Klerno Labs.
Provides consistent, structured logging throughout the application.
"""

import logging
import sys
from datetime import UTC, datetime
from typing import Any

import structlog
try:
    from pythonjsonlogger.json import JsonFormatter
except Exception:  # pragma: no cover - optional dependency in some envs
    JsonFormatter = None  # type: ignore[assignment]

from app.settings import get_settings


def _to_iso(timestamp: Any) -> str:
    """Safely convert timestamp-like values to ISO string for logging."""
    try:
        if timestamp is None:
            return datetime.now(UTC).isoformat()
        if isinstance(timestamp, str):
            return timestamp
        iso = getattr(timestamp, "isoformat", None)
        if callable(iso):
            return str(iso())
        if isinstance(timestamp, (int, float)):
            return datetime.fromtimestamp(timestamp, UTC).isoformat()
        return str(timestamp)
    except Exception:
        return datetime.now(UTC).isoformat()


def configure_logging() -> None:
    """Configure structured logging for the application."""
    settings = get_settings()

    # Map app_env to valid logging levels
    env_to_level = {
        "production": "INFO",
        "prod": "INFO",
        "staging": "INFO",
        "stage": "INFO",
        "development": "DEBUG",
        "dev": "DEBUG",
        "test": "DEBUG",
    }
    app_env = getattr(settings, "app_env", None) or "development"
    log_level_str = env_to_level.get(str(app_env).lower(), "DEBUG")
    log_level = getattr(logging, log_level_str)

    # Remove existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # JSON formatter for structured logs (fallback to basic if missing)
    if JsonFormatter is not None:
        json_formatter = JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        json_formatter = logging.Formatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    # File handler for Promtail/Loki
    # Ensure logs directory exists to avoid FileNotFoundError on startup/tests
    from contextlib import suppress
    from pathlib import Path

    logs_path = Path("logs")
    with suppress(Exception):
        logs_path.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(
        str(logs_path / "app.log"),
        mode="a",
        encoding="utf-8",
    )

    if settings.app_env == "production":
        console_handler.setFormatter(json_formatter)
        file_handler.setFormatter(json_formatter)
    else:
        # Human-readable format for development
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%H:%M:%S",
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(json_formatter)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        handlers=[console_handler, file_handler],
        force=True,
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            (
                # ConsoleRenderer returns an object that mypy may not infer as a Callable;
                # use typing.cast to silence the list-item typing warning.
                __import__("typing").cast(
                    __import__("typing").Any,
                    (
                        structlog.dev.ConsoleRenderer()
                        if settings.app_env == "dev"
                        else structlog.processors.JSONRenderer()
                    ),
                )
            ),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        # Use the stdlib LoggerFactory so processors (which expect a logging.Logger)
        # can access attributes like .name without error. PrintLoggerFactory returns
        # a lightweight PrintLogger that doesn't expose the full API needed.
        logger_factory=structlog.stdlib.LoggerFactory(),
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
    request_id: str | None = None,
    user_id: str | None = None,
    **kwargs: Any,
) -> None:
    """Log HTTP request / response details."""
    logger = get_logger("http")

    log_data: dict[str, Any] = {
        "method": method,
        "url": url,
        "status_code": status_code,
        "duration_ms": round(duration * 1000, 2),
        "timestamp": datetime.now(UTC).isoformat(),
    }

    if request_id:
        log_data["request_id"] = request_id

    if user_id:
        log_data["user_id"] = user_id

    if kwargs:
        from contextlib import suppress

        with suppress(Exception):
            log_data.update(dict(kwargs))

    if status_code >= 500:
        logger.error("HTTP request failed", **log_data)
    elif status_code >= 400:
        logger.warning("HTTP request error", **log_data)
    else:
        logger.info("HTTP request", **log_data)


def log_security_event(
    event_type: str,
    user_id: str | None = None,
    ip_address: str | None = None,
    details: dict[str, Any] | None = None,
    **kwargs: Any,
) -> None:
    """Log security - related events."""
    logger = get_logger("security")

    log_data: dict[str, Any] = {
        "event_type": event_type,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    if user_id:
        log_data["user_id"] = user_id

    if ip_address:
        log_data["ip_address"] = ip_address

    if details:
        try:
            log_data["details"] = (
                dict(details) if not isinstance(details, str) else details
            )
        except Exception:
            log_data["details"] = str(details)

    if kwargs:
        from contextlib import suppress

        with suppress(Exception):
            log_data.update(dict(kwargs))

    # Security events are always important
    if event_type in [
        "authentication_failure",
        "authorization_failure",
        "suspicious_activity",
    ]:
        logger.warning("Security event", **log_data)
    else:
        logger.info("Security event", **log_data)


def log_business_event(
    event_type: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    user_id: str | None = None,
    details: dict[str, Any] | None = None,
    **kwargs: Any,
) -> None:
    """Log business logic events."""
    logger = get_logger("business")

    log_data: dict[str, Any] = {
        "event_type": event_type,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    if entity_type:
        log_data["entity_type"] = entity_type

    if entity_id:
        log_data["entity_id"] = entity_id

    if user_id:
        log_data["user_id"] = user_id

    if details:
        try:
            log_data["details"] = (
                dict(details) if not isinstance(details, str) else details
            )
        except Exception:
            log_data["details"] = str(details)

    if kwargs:
        from contextlib import suppress

        with suppress(Exception):
            log_data.update(dict(kwargs))

    logger.info("Business event", **log_data)


def log_performance_metric(
    operation: str,
    duration: float,
    success: bool = True,
    details: dict[str, Any] | None = None,
    **kwargs: Any,
) -> None:
    """Log performance metrics."""
    logger = get_logger("performance")

    log_data: dict[str, Any] = {
        "operation": operation,
        "duration_ms": round(duration * 1000, 2),
        "success": success,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    if details:
        try:
            log_data["details"] = (
                dict(details) if not isinstance(details, str) else details
            )
        except Exception:
            log_data["details"] = str(details)

    if kwargs:
        from contextlib import suppress

        with suppress(Exception):
            log_data.update(dict(kwargs))

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
