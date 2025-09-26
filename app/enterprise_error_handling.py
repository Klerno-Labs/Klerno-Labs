"""
Klerno Labs Enterprise Error Handling & Circuit Breaker System
Advanced error handling, circuit breakers, and failover mechanisms
"""

import functools
import json
import logging
import sqlite3
import threading
import time
import traceback
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from .resilience_system import circuit_breaker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class ErrorSeverity(Enum):
    """Error severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorEvent:
    """Error event record"""

    timestamp: datetime
    error_type: str
    error_message: str
    severity: ErrorSeverity
    service: str
    stack_trace: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolution_time: datetime | None = None


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""

    failure_threshold: int = 5
    recovery_timeout: int = 60
    expected_exception: type[BaseException] = Exception
    success_threshold: int = 3
    timeout: int = 30


class EnterpriseCircuitBreaker:
    """Advanced circuit breaker with monitoring"""

    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count: int = 0
        self.success_count: int = 0
        self.last_failure_time: float | None = None
        self.stats: dict[str, Any] = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "circuit_opened_count": 0,
            "last_opened": None,
            "avg_response_time": 0.0,
        }
        self._lock = threading.RLock()

        logger.info(
            f"[CIRCUIT] Created circuit breaker '{name}' with threshold {config.failure_threshold}"
        )

    def __call__(self, func: Callable) -> Callable:
        """Decorator for protecting functions with circuit breaker"""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)

        return wrapper

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        with self._lock:
            self.stats["total_calls"] += 1

            # Check circuit state
            if self.state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitBreakerState.HALF_OPEN
                    logger.info(f"[CIRCUIT] {self.name} transitioning to HALF_OPEN")
                else:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker {self.name} is OPEN"
                    )

            # Execute function
            start_time = time.time()

            try:
                result = func(*args, **kwargs)

                # Record success
                execution_time = time.time() - start_time
                self._record_success(execution_time)

                return result

            except self.config.expected_exception as e:
                # Record failure
                execution_time = time.time() - start_time
                self._record_failure(e, execution_time)
                raise

    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset"""
        if self.last_failure_time is None:
            return False

        return (time.time() - self.last_failure_time) >= self.config.recovery_timeout

    def _record_success(self, execution_time: float):
        """Record successful execution"""
        # Ensure numeric types
        self.stats["successful_calls"] = int(self.stats.get("successful_calls", 0)) + 1
        self.stats["failed_calls"] = int(self.stats.get("failed_calls", 0))

        # Update average response time safely
        total_calls = int(self.stats["successful_calls"]) + int(
            self.stats["failed_calls"]
        )
        if total_calls <= 0:
            self.stats["avg_response_time"] = float(execution_time)
        else:
            prev_avg = float(self.stats.get("avg_response_time", 0.0))
            self.stats["avg_response_time"] = (
                prev_avg * (total_calls - 1) + execution_time
            ) / max(1, total_calls)

        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1

            if self.success_count >= self.config.success_threshold:
                self._close_circuit()
        else:
            self.failure_count = 0

    def _record_failure(self, exception: BaseException, execution_time: float):
        """Record failed execution"""
        # Ensure numeric types and safe updates
        self.stats["failed_calls"] = int(self.stats.get("failed_calls", 0)) + 1
        self.failure_count += 1
        self.last_failure_time = float(time.time())

        total_calls = int(self.stats.get("successful_calls", 0)) + int(
            self.stats.get("failed_calls", 0)
        )
        prev_avg = float(self.stats.get("avg_response_time", 0.0))
        if total_calls <= 0:
            self.stats["avg_response_time"] = float(execution_time)
        else:
            self.stats["avg_response_time"] = (
                prev_avg * (total_calls - 1) + execution_time
            ) / max(1, total_calls)

        if (
            self.state == CircuitBreakerState.HALF_OPEN
            or self.failure_count >= self.config.failure_threshold
        ):
            self._open_circuit()

        logger.warning(
            f"[CIRCUIT] {self.name} failure {self.failure_count}/{self.config.failure_threshold}: {exception}"
        )

    def _open_circuit(self):
        """Open the circuit"""
        self.state = CircuitBreakerState.OPEN
        self.stats["circuit_opened_count"] += 1
        self.stats["last_opened"] = datetime.now().isoformat()
        logger.error(
            f"[CIRCUIT] {self.name} OPENED after {self.failure_count} failures"
        )

    def _close_circuit(self):
        """Close the circuit"""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        logger.info(f"[CIRCUIT] {self.name} CLOSED - service recovered")

    def get_stats(self) -> dict[str, Any]:
        """Get circuit breaker statistics"""
        with self._lock:
            return {
                "name": self.name,
                "state": self.state.value,
                "failure_count": self.failure_count,
                "config": {
                    "failure_threshold": self.config.failure_threshold,
                    "recovery_timeout": self.config.recovery_timeout,
                    "success_threshold": self.config.success_threshold,
                },
                "stats": self.stats.copy(),
            }


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open"""

    pass


class EnterpriseErrorHandler:
    """Comprehensive error handling system"""

    def __init__(self, database_path: str = "./data/klerno.db"):
        self.database_path = database_path
        self.error_events: list[ErrorEvent] = []
        self.circuit_breakers: dict[str, EnterpriseCircuitBreaker] = {}
        self.error_handlers: dict[str, Callable] = {}
        self.auto_recovery_handlers: dict[str, Callable] = {}

        self._lock = threading.RLock()
        self._init_database()

        # Start error monitoring thread
        self._monitoring_thread = threading.Thread(
            target=self._monitor_errors, daemon=True
        )
        self._monitoring_thread.start()

        logger.info("[ERROR-HANDLER] Enterprise error handling system initialized")

        # Provide resilience decorator compatibility
        self.circuit_breaker = circuit_breaker

    def _init_database(self):
        """Initialize error tracking database"""
        try:
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)

            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()

            # Create error events table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS error_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    error_type TEXT NOT NULL,
                    error_message TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    service TEXT NOT NULL,
                    stack_trace TEXT,
                    context TEXT,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolution_time TEXT
                )
            """
            )

            # Create circuit breaker events table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS circuit_breaker_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    breaker_name TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    details TEXT
                )
            """
            )

            conn.commit()
            conn.close()

            logger.info("[ERROR-HANDLER] Database initialized")

        except Exception as e:
            logger.error(f"[ERROR-HANDLER] Database initialization failed: {e}")

    def create_circuit_breaker(
        self, name: str, config: CircuitBreakerConfig
    ) -> EnterpriseCircuitBreaker:
        """Create a new circuit breaker"""
        with self._lock:
            if name in self.circuit_breakers:
                return self.circuit_breakers[name]

            breaker = EnterpriseCircuitBreaker(name, config)
            self.circuit_breakers[name] = breaker

            logger.info(f"[ERROR-HANDLER] Created circuit breaker: {name}")
            return breaker

    def get_circuit_breaker(self, name: str) -> EnterpriseCircuitBreaker | None:
        """Get existing circuit breaker"""
        return self.circuit_breakers.get(name)

    def register_error_handler(self, error_type: str, handler: Callable):
        """Register custom error handler"""
        self.error_handlers[error_type] = handler
        logger.info(f"[ERROR-HANDLER] Registered handler for {error_type}")

    def register_auto_recovery(self, service: str, recovery_handler: Callable):
        """Register auto-recovery handler"""
        self.auto_recovery_handlers[service] = recovery_handler
        logger.info(f"[ERROR-HANDLER] Registered auto-recovery for {service}")

    def handle_error(
        self,
        error: Exception,
        service: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: dict[str, Any] | None = None,
    ) -> ErrorEvent:
        """Handle and record error event"""

        error_event = ErrorEvent(
            timestamp=datetime.now(),
            error_type=type(error).__name__,
            error_message=str(error),
            severity=severity,
            service=service,
            stack_trace=traceback.format_exc(),
            context=context or {},
        )

        with self._lock:
            self.error_events.append(error_event)

            # Store in database
            self._store_error_event(error_event)

            # Check for custom handler
            error_type = error_event.error_type
            if error_type in self.error_handlers:
                try:
                    self.error_handlers[error_type](error_event)
                except Exception as handler_error:
                    logger.error(f"[ERROR-HANDLER] Handler failed: {handler_error}")

            # Check for auto-recovery
            if service in self.auto_recovery_handlers:
                try:
                    self.auto_recovery_handlers[service](error_event)
                    logger.info(
                        f"[ERROR-HANDLER] Auto-recovery triggered for {service}"
                    )
                except Exception as recovery_error:
                    logger.error(
                        f"[ERROR-HANDLER] Auto-recovery failed: {recovery_error}"
                    )

            # Log error based on severity
            if severity == ErrorSeverity.CRITICAL:
                logger.critical(f"[ERROR-HANDLER] CRITICAL ERROR in {service}: {error}")
            elif severity == ErrorSeverity.HIGH:
                logger.error(f"[ERROR-HANDLER] HIGH ERROR in {service}: {error}")
            elif severity == ErrorSeverity.MEDIUM:
                logger.warning(f"[ERROR-HANDLER] MEDIUM ERROR in {service}: {error}")
            else:
                logger.info(f"[ERROR-HANDLER] LOW ERROR in {service}: {error}")

        return error_event

    def _store_error_event(self, event: ErrorEvent):
        """Store error event in database"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO error_events
                (timestamp, error_type, error_message, severity, service, stack_trace, context)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    event.timestamp.isoformat(),
                    event.error_type,
                    event.error_message,
                    event.severity.value,
                    event.service,
                    event.stack_trace,
                    json.dumps(event.context),
                ),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"[ERROR-HANDLER] Failed to store error event: {e}")

    def _monitor_errors(self):
        """Monitor errors and trigger alerts"""
        while True:
            try:
                time.sleep(60)  # Check every minute

                with self._lock:
                    # Check error rates
                    recent_errors = [
                        e
                        for e in self.error_events
                        if (datetime.now() - e.timestamp).total_seconds()
                        < 300  # Last 5 minutes
                    ]

                    if len(recent_errors) > 10:  # More than 10 errors in 5 minutes
                        logger.warning(
                            f"[ERROR-HANDLER] High error rate: {len(recent_errors)} errors in 5 minutes"
                        )

                    # Check for critical errors
                    critical_errors = [
                        e
                        for e in recent_errors
                        if e.severity == ErrorSeverity.CRITICAL and not e.resolved
                    ]

                    if critical_errors:
                        logger.critical(
                            f"[ERROR-HANDLER] {len(critical_errors)} unresolved critical errors"
                        )

            except Exception as e:
                logger.error(f"[ERROR-HANDLER] Monitoring error: {e}")

    def get_error_summary(self, hours: int = 24) -> dict[str, Any]:
        """Get error summary for the last N hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        with self._lock:
            recent_errors = [e for e in self.error_events if e.timestamp >= cutoff_time]

            # Group by service
            service_errors: dict[str, list[ErrorEvent]] = {}
            severity_counts = {severity.value: 0 for severity in ErrorSeverity}

            for error in recent_errors:
                service = error.service
                if service not in service_errors:
                    service_errors[service] = []
                service_errors[service].append(error)
                severity_counts[error.severity.value] += 1

            # Circuit breaker stats
            breaker_stats = {}
            for name, breaker in self.circuit_breakers.items():
                breaker_stats[name] = breaker.get_stats()

            return {
                "time_period_hours": hours,
                "total_errors": len(recent_errors),
                "errors_by_service": {
                    service: len(errors) for service, errors in service_errors.items()
                },
                "errors_by_severity": severity_counts,
                "circuit_breakers": breaker_stats,
                "unresolved_critical": len(
                    [
                        e
                        for e in recent_errors
                        if e.severity == ErrorSeverity.CRITICAL and not e.resolved
                    ]
                ),
            }

        # Compatibility alias expected by other modules
        def get_error_statistics(self) -> dict[str, Any]:
            """Alias for get_error_summary to match legacy API"""
            # Provide a compact summary suitable for metrics
            summary = self.get_error_summary(1)
            return {
                "total_errors": summary.get("total_errors", 0),
                "error_rate": summary.get("total_errors", 0) / 1.0,
                "circuit_breaker_state": {
                    name: cb.get_stats() for name, cb in self.circuit_breakers.items()
                },
            }

    @contextmanager
    def error_context(
        self, service: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ):
        """Context manager for automatic error handling"""
        try:
            yield
        except Exception as e:
            self.handle_error(e, service, severity)
            raise


# Decorators for error handling
def handle_errors(service: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM):
    """Decorator for automatic error handling"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler.handle_error(e, service, severity)
                raise

        return wrapper

    return decorator


def with_circuit_breaker(breaker_name: str, config: CircuitBreakerConfig | None = None):
    """Decorator for circuit breaker protection"""

    def decorator(func: Callable) -> Callable:
        # Create circuit breaker if it doesn't exist
        if config is not None:
            breaker = error_handler.create_circuit_breaker(breaker_name, config)
        else:
            existing = error_handler.get_circuit_breaker(breaker_name)
            if existing is not None:
                breaker = existing
            else:
                default_config = CircuitBreakerConfig()
                breaker = error_handler.create_circuit_breaker(
                    breaker_name, default_config
                )

        return breaker(func)

    return decorator


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator for automatic retry with exponential backoff"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception: Exception | None = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt < max_retries:
                        logger.warning(
                            f"[RETRY] Attempt {attempt + 1} failed, retrying in {current_delay}s: {e}"
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"[RETRY] All {max_retries + 1} attempts failed")
                        if last_exception is not None:
                            raise last_exception
                        raise RuntimeError(
                            "Retry attempts exhausted"
                        ) from last_exception

            # Fallback in case loop exits unexpectedly
            if last_exception is not None:
                raise last_exception
            raise RuntimeError("Retry attempts exhausted") from last_exception

        return wrapper

    return decorator


# Global error handler instance
error_handler = EnterpriseErrorHandler()


def initialize_error_handling():
    """Initialize enterprise error handling"""
    try:
        # Create default circuit breakers
        database_config = CircuitBreakerConfig(
            failure_threshold=5, recovery_timeout=30, expected_exception=Exception
        )

        payment_config = CircuitBreakerConfig(
            failure_threshold=3, recovery_timeout=60, expected_exception=Exception
        )

        api_config = CircuitBreakerConfig(
            failure_threshold=10, recovery_timeout=30, expected_exception=Exception
        )

        error_handler.create_circuit_breaker("database", database_config)
        error_handler.create_circuit_breaker("payment_processing", payment_config)
        error_handler.create_circuit_breaker("external_api", api_config)

        logger.info(
            "[ERROR-HANDLER] Enterprise error handling initialized with default circuit breakers"
        )
        return error_handler

    except Exception as e:
        logger.error(f"[ERROR-HANDLER] Initialization failed: {e}")
        return error_handler


def get_error_handler() -> EnterpriseErrorHandler:
    """Compatibility shim: return the global error handler instance."""
    return error_handler


if __name__ == "__main__":
    # Test the error handling system
    handler = initialize_error_handling()

    # Test circuit breaker
    @with_circuit_breaker("test_service")
    def unreliable_function(should_fail=False):
        if should_fail:
            raise Exception("Test failure")
        return "Success"

    # Test error handling
    try:
        # This should work
        result = unreliable_function(False)
        print(f"Success: {result}")

        # This should trigger circuit breaker
        for i in range(6):
            try:
                unreliable_function(True)
            except Exception as e:
                print(f"Expected failure {i + 1}: {e}")

        # Get error summary
        summary = handler.get_error_summary(1)
        print(f"Error summary: {json.dumps(summary, indent=2)}")

    except Exception as e:
        print(f"Test error: {e}")
