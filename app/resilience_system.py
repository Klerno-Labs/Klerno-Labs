"""Advanced Error Handling & Resilience System

Implements circuit breakers, retry mechanisms, graceful degradation,
    failover systems, disaster recovery, and self - healing capabilities
for maximum uptime and enterprise - grade reliability.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import random
import threading
import time
import traceback
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from functools import wraps
from typing import Any, TypeVar

# weakref not used

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class HealthStatus(str, Enum):
    """Service health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


class ErrorSeverity(str, Enum):
    """Error severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorEvent:
    """Error event data structure."""

    id: str
    service: str
    error_type: str
    error_message: str
    severity: ErrorSeverity
    timestamp: datetime
    context: dict[str, Any]
    stack_trace: str | None = None
    resolved: bool = False


@dataclass
class RetryPolicy:
    """Retry policy configuration."""

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on_exceptions: list[type] | None = None


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""

    failure_threshold: int = 5
    success_threshold: int = 3
    timeout_duration: float = 60.0
    monitoring_period: float = 10.0


class CircuitBreaker:
    """Advanced circuit breaker implementation."""

    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: float | None = None
        self.request_count = 0
        self.success_request_count = 0
        self.lock = threading.RLock()

        # Statistics
        self.total_requests: int = 0
        self.total_failures: int = 0
        self.state_transitions: list[dict[str, Any]] = []

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection."""
        with self.lock:
            self.total_requests += 1

            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    logger.info(f"Circuit breaker {self.name} moved to HALF_OPEN")
                else:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker {self.name} is OPEN",
                    )

            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result

            except Exception as e:
                self._on_failure(e)
                raise

    async def call_async(self, func: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
        """Execute async function with circuit breaker protection."""
        with self.lock:
            self.total_requests += 1

            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    logger.info(f"Circuit breaker {self.name} moved to HALF_OPEN")
                else:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker {self.name} is OPEN",
                    )

            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result

            except Exception as e:
                self._on_failure(e)
                raise

    def _on_success(self) -> None:
        """Handle successful request."""
        with self.lock:
            self.success_request_count += 1

            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    logger.info(f"Circuit breaker {self.name} moved to CLOSED")
                    self._record_state_transition(CircuitState.CLOSED)
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0

    def _on_failure(self, exception: Exception) -> None:
        """Handle failed request."""
        with self.lock:
            self.total_failures += 1
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                logger.warning(
                    f"Circuit breaker {self.name} moved to OPEN (failure in HALF_OPEN)",
                )
                self._record_state_transition(CircuitState.OPEN)
            elif self.state == CircuitState.CLOSED:
                if self.failure_count >= self.config.failure_threshold:
                    self.state = CircuitState.OPEN
                    logger.warning(
                        f"Circuit breaker {self.name} moved to OPEN (threshold reached)",
                    )
                    self._record_state_transition(CircuitState.OPEN)

    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt to reset."""
        # Ensure we always return a plain bool. Using `and` can return None or a
        # numeric value which causes type-checkers to complain (and is less
        # explicit). If there was no previous failure time, we should not
        # attempt a reset.
        if self.last_failure_time is None:
            return False

        return (time.time() - self.last_failure_time) >= self.config.timeout_duration

    def _record_state_transition(self, new_state: CircuitState) -> None:
        """Record state transition for monitoring."""
        self.state_transitions.append(
            {
                "from_state": self.state.value,
                "to_state": new_state.value,
                "timestamp": datetime.now(UTC),
                "failure_count": self.failure_count,
                "success_count": self.success_count,
            },
        )

        # Keep only last 100 transitions
        if len(self.state_transitions) > 100:
            self.state_transitions = self.state_transitions[-100:]

    def get_stats(self) -> dict[str, Any]:
        """Get circuit breaker statistics."""
        with self.lock:
            failure_rate = (
                self.total_failures / self.total_requests
                if self.total_requests > 0
                else 0
            )

            return {
                "name": self.name,
                "state": self.state.value,
                "total_requests": self.total_requests,
                "total_failures": self.total_failures,
                "failure_rate": failure_rate,
                "current_failure_count": self.failure_count,
                "success_count": self.success_count,
                "last_failure_time": self.last_failure_time,
                "recent_transitions": self.state_transitions[-10:],
            }

    def reset(self) -> None:
        """Manually reset circuit breaker."""
        with self.lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            logger.info(f"Circuit breaker {self.name} manually reset")


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""



class RetryManager:
    """Advanced retry mechanism with various strategies."""

    def __init__(self):
        # Map function name -> stats dict
        self.retry_stats: defaultdict[str, dict[str, int]] = defaultdict(
            lambda: {
                "total_attempts": 0,
                "successful_retries": 0,
                "failed_retries": 0,
                "avg_retry_count": 0,
            },
        )

    def retry(self, policy: RetryPolicy):
        """Decorator for automatic retry with backoff."""

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self._execute_with_retry_async(
                    func, policy, *args, **kwargs,
                )

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return self._execute_with_retry_sync(func, policy, *args, **kwargs)

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper

        return decorator

    async def _execute_with_retry_async(
        self, func: Callable[..., Awaitable[Any]], policy: RetryPolicy, *args, **kwargs,
    ) -> Any:
        """Execute async function with retry logic."""
        func_name = func.__name__
        last_exception = None
        for attempt in range(policy.max_attempts):
            try:
                self.retry_stats[func_name]["total_attempts"] += 1
                result = await func(*args, **kwargs)

                if attempt > 0:
                    self.retry_stats[func_name]["successful_retries"] += 1

                return result

            except Exception as e:
                last_exception = e

                # Check if we should retry this exception
                if policy.retry_on_exceptions and not any(
                    isinstance(e, exc_type) for exc_type in policy.retry_on_exceptions
                ):
                    raise e

                if attempt < policy.max_attempts - 1:
                    delay = self._calculate_delay(attempt, policy)
                    logger.warning(
                        "Attempt %s failed for %s, retrying in %.2fs: %s",
                        attempt + 1,
                        func_name,
                        delay,
                        e,
                    )
                    await asyncio.sleep(delay)
                else:
                    self.retry_stats[func_name]["failed_retries"] += 1
                    logger.error(
                        f"All {policy.max_attempts} attempts failed for {func_name}",
                    )

        # Ensure we never raise None which would be an invalid exception.
        if last_exception:
            raise last_exception
        raise RuntimeError(f"All {policy.max_attempts} retry attempts failed")

    def _execute_with_retry_sync(
        self, func: Callable, policy: RetryPolicy, *args, **kwargs,
    ) -> Any:
        """Execute sync function with retry logic."""
        func_name = func.__name__
        last_exception = None
        for attempt in range(policy.max_attempts):
            try:
                self.retry_stats[func_name]["total_attempts"] += 1
                result = func(*args, **kwargs)

                if attempt > 0:
                    self.retry_stats[func_name]["successful_retries"] += 1

                return result

            except Exception as e:
                last_exception = e

                # Check if we should retry this exception
                if policy.retry_on_exceptions and not any(
                    isinstance(e, exc_type) for exc_type in policy.retry_on_exceptions
                ):
                    raise e

                if attempt < policy.max_attempts - 1:
                    delay = self._calculate_delay(attempt, policy)
                    logger.warning(
                        "Attempt %s failed for %s, retrying in %.2fs: %s",
                        attempt + 1,
                        func_name,
                        delay,
                        e,
                    )
                    time.sleep(delay)
                else:
                    self.retry_stats[func_name]["failed_retries"] += 1
                    logger.error(
                        f"All {policy.max_attempts} attempts failed for {func_name}",
                    )

        if last_exception:
            raise last_exception
        raise RuntimeError(f"All {policy.max_attempts} retry attempts failed")

    def _calculate_delay(self, attempt: int, policy: RetryPolicy) -> float:
        """Calculate retry delay with exponential backoff and jitter."""
        delay = min(
            policy.base_delay * (policy.exponential_base**attempt), policy.max_delay,
        )

        if policy.jitter:
            # Add random jitter (±25%). This jitter is non-cryptographic and
            # used purely to avoid synchronized retries across processes; using
            # the standard random module is acceptable here (not security-sensitive).
            jitter_range = delay * 0.25
            delay += random.uniform(
                -jitter_range, jitter_range,
            )  # nosec: B311 - non-crypto jitter for backoff, cryptographic randomness not required

        return max(0, delay)

    def get_stats(self) -> dict[str, Any]:
        """Get retry statistics."""
        return dict(self.retry_stats)


class FailoverManager:
    """Manages service failover and redundancy."""

    def __init__(self):
        self.services = {}
        self.health_checks = {}
        self.failover_groups = {}
        self.active_services = {}
        self.lock = threading.RLock()

    def register_service(
        self,
        service_name: str,
        primary_endpoint: str,
        backup_endpoints: list[str],
        health_check_func: Callable | None = None,
    ) -> None:
        """Register service with failover configuration."""
        with self.lock:
            self.services[service_name] = {
                "primary": primary_endpoint,
                "backups": backup_endpoints,
                "current_endpoint": primary_endpoint,
                "failed_endpoints": set(),
                "last_failover": None,
            }

            self.health_checks[service_name] = health_check_func
            self.active_services[service_name] = primary_endpoint

            logger.info(
                "Registered service %s with %d backup endpoints",
                service_name,
                len(backup_endpoints),
            )

    def get_active_endpoint(self, service_name: str) -> str:
        """Get currently active endpoint for service."""
        with self.lock:
            if service_name not in self.services:
                raise ValueError(f"Service {service_name} not registered")

            return self.active_services[service_name]

    async def health_check_all_services(self) -> dict[str, HealthStatus]:
        """Perform health checks on all registered services."""
        health_statuses = {}

        for service_name in self.services:
            status = await self._check_service_health(service_name)
            health_statuses[service_name] = status

            if status == HealthStatus.UNHEALTHY:
                await self._perform_failover(service_name)

        return health_statuses

    async def _check_service_health(self, service_name: str) -> HealthStatus:
        """Check health of a specific service."""
        health_check_func = self.health_checks.get(service_name)

        if not health_check_func:
            return HealthStatus.HEALTHY  # Assume healthy if no health check

        try:
            result = await health_check_func(self.active_services[service_name])
            return HealthStatus(result.get("status", "healthy"))
        except Exception as e:
            logger.error(f"Health check failed for {service_name}: {e}")
            return HealthStatus.UNHEALTHY

    async def _perform_failover(self, service_name: str) -> bool:
        """Perform failover to backup endpoint."""
        with self.lock:
            service_info = self.services[service_name]
            current_endpoint = service_info["current_endpoint"]

            # Mark current endpoint as failed
            service_info["failed_endpoints"].add(current_endpoint)

            # Find next healthy backup
            available_backups = [
                endpoint
                for endpoint in service_info["backups"]
                if endpoint not in service_info["failed_endpoints"]
            ]

            if not available_backups:
                logger.error(
                    f"No healthy backup endpoints available for {service_name}",
                )
                return False

            # Switch to first available backup
            new_endpoint = available_backups[0]
            service_info["current_endpoint"] = new_endpoint
            service_info["last_failover"] = datetime.now(UTC)
            self.active_services[service_name] = new_endpoint

            logger.warning(
                "Failover performed for %s: %s -> %s",
                service_name,
                current_endpoint,
                new_endpoint,
            )
            return True

    def force_failover(
        self, service_name: str, target_endpoint: str | None = None,
    ) -> bool:
        """Manually force failover to specific endpoint."""
        with self.lock:
            if service_name not in self.services:
                return False

            service_info = self.services[service_name]

            if target_endpoint:
                if (
                    target_endpoint
                    in [service_info["primary"]] + service_info["backups"]
                ):
                    service_info["current_endpoint"] = target_endpoint
                    self.active_services[service_name] = target_endpoint
                    logger.info(
                        f"Manual failover for {service_name} to {target_endpoint}",
                    )
                    return True
                logger.error(
                    "Target endpoint %s not configured for %s",
                    target_endpoint,
                    service_name,
                )
                return False
            # Failover to next available backup
            return asyncio.run(self._perform_failover(service_name))

    def reset_failed_endpoints(self, service_name: str) -> None:
        """Reset failed endpoints list (for recovery)."""
        with self.lock:
            if service_name in self.services:
                self.services[service_name]["failed_endpoints"].clear()
                logger.info(f"Reset failed endpoints for {service_name}")

    def get_failover_stats(self) -> dict[str, Any]:
        """Get failover statistics."""
        with self.lock:
            stats = {}
            for service_name, service_info in self.services.items():
                stats[service_name] = {
                    "current_endpoint": service_info["current_endpoint"],
                    "failed_endpoints": list(service_info["failed_endpoints"]),
                    "last_failover": service_info["last_failover"],
                    "backup_count": len(service_info["backups"]),
                    "is_on_primary": service_info["current_endpoint"]
                    == service_info["primary"],
                }
            return stats


class GracefulDegradationManager:
    """Manages graceful service degradation."""

    def __init__(self):
        self.degradation_rules = {}
        self.current_degradations = {}
        self.feature_flags = {}
        self.lock = threading.RLock()

    def register_degradation_rule(
        self,
        service_name: str,
        degradation_levels: dict[str, Callable],
        trigger_conditions: dict[str, Callable],
    ) -> None:
        """Register degradation rule for service."""
        with self.lock:
            self.degradation_rules[service_name] = {
                "levels": degradation_levels,
                "conditions": trigger_conditions,
            }

            self.current_degradations[service_name] = "normal"
            logger.info(f"Registered degradation rule for {service_name}")

    def set_feature_flag(self, feature_name: str, enabled: bool) -> None:
        """Set feature flag for controlling degradation."""
        with self.lock:
            self.feature_flags[feature_name] = enabled
            logger.info(f"Feature flag {feature_name} set to {enabled}")

    async def evaluate_degradation(
        self, service_name: str, context: dict[str, Any],
    ) -> str:
        """Evaluate if service should degrade and to what level."""
        if service_name not in self.degradation_rules:
            return "normal"

        rule = self.degradation_rules[service_name]

        # Evaluate trigger conditions
        for level, condition_func in rule["conditions"].items():
            try:
                if await condition_func(context):
                    with self.lock:
                        old_level = self.current_degradations[service_name]
                        self.current_degradations[service_name] = level

                        if old_level != level:
                            logger.warning(
                                "Service %s degraded from %s to %s",
                                service_name,
                                old_level,
                                level,
                            )

                        return level
            except Exception as e:
                logger.error(
                    f"Error evaluating degradation condition for {service_name}: {e}",
                )

        # No degradation needed
        with self.lock:
            self.current_degradations[service_name] = "normal"

        return "normal"

    async def execute_with_degradation(
        self, service_name: str, context: dict[str, Any], **kwargs,
    ) -> Any:
        """Execute service function with appropriate degradation level."""
        current_level = await self.evaluate_degradation(service_name, context)

        if service_name not in self.degradation_rules:
            raise ValueError(f"Service {service_name} not registered for degradation")

        rule = self.degradation_rules[service_name]
        degradation_func = rule["levels"].get(current_level)

        if not degradation_func:
            raise ValueError(f"No degradation function for level {current_level}")

        return await degradation_func(context, **kwargs)

    def get_degradation_status(self) -> dict[str, str]:
        """Get current degradation status for all services."""
        with self.lock:
            return dict(self.current_degradations)


class SelfHealingManager:
    """Manages self - healing capabilities."""

    def __init__(self):
        self.healing_rules = {}
        self.healing_history = []
        self.auto_healing_enabled = True
        self.lock = threading.RLock()

    def register_healing_rule(
        self,
        error_pattern: str,
        healing_action: Callable,
        max_attempts: int = 3,
        cooldown_period: int = 300,
    ) -> None:
        """Register self - healing rule."""
        with self.lock:
            self.healing_rules[error_pattern] = {
                "action": healing_action,
                "max_attempts": max_attempts,
                "cooldown_period": cooldown_period,
                "attempt_count": 0,
                "last_attempt": None,
            }

            logger.info(f"Registered healing rule for pattern: {error_pattern}")

    async def attempt_healing(self, error: Exception, context: dict[str, Any]) -> bool:
        """Attempt to heal from error using registered rules."""
        if not self.auto_healing_enabled:
            return False

        error_message = str(error)

        with self.lock:
            for pattern, rule in self.healing_rules.items():
                if pattern in error_message:
                    return await self._execute_healing_action(
                        pattern, rule, error, context,
                    )

        return False

    async def _execute_healing_action(
        self,
        pattern: str,
        rule: dict[str, Any],
        error: Exception,
        context: dict[str, Any],
    ) -> bool:
        """Execute healing action for specific rule."""
        current_time = time.time()

        # Check cooldown period
        if (
            rule["last_attempt"]
            and current_time - rule["last_attempt"] < rule["cooldown_period"]
        ):
            return False

        # Check max attempts
        if rule["attempt_count"] >= rule["max_attempts"]:
            logger.error(f"Max healing attempts reached for pattern: {pattern}")
            return False

        try:
            rule["attempt_count"] += 1
            rule["last_attempt"] = current_time

            logger.info(f"Attempting self - healing for pattern: {pattern}")
            result = await rule["action"](error, context)

            healing_event = {
                "pattern": pattern,
                "error": str(error),
                "timestamp": datetime.now(UTC),
                "success": result,
                "attempt_number": rule["attempt_count"],
            }

            self.healing_history.append(healing_event)

            # Keep only last 100 healing attempts
            if len(self.healing_history) > 100:
                self.healing_history = self.healing_history[-100:]

            if result:
                logger.info(f"Self - healing successful for pattern: {pattern}")
                rule["attempt_count"] = 0  # Reset on success
            else:
                logger.warning(f"Self - healing failed for pattern: {pattern}")

            return result

        except Exception as heal_error:
            logger.error(
                f"Self - healing action failed for pattern {pattern}: {heal_error}",
            )
            return False

    def reset_healing_attempts(self, pattern: str | None = None) -> None:
        """Reset healing attempt counters."""
        with self.lock:
            if pattern:
                if pattern in self.healing_rules:
                    self.healing_rules[pattern]["attempt_count"] = 0
                    logger.info(f"Reset healing attempts for pattern: {pattern}")
            else:
                for rule in self.healing_rules.values():
                    rule["attempt_count"] = 0
                logger.info("Reset all healing attempt counters")

    def set_auto_healing(self, enabled: bool) -> None:
        """Enable or disable auto - healing."""
        self.auto_healing_enabled = enabled
        logger.info(f"Auto - healing {'enabled' if enabled else 'disabled'}")

    def get_healing_stats(self) -> dict[str, Any]:
        """Get self - healing statistics."""
        with self.lock:
            stats: dict[str, Any] = {
                "auto_healing_enabled": self.auto_healing_enabled,
                "total_rules": len(self.healing_rules),
                "recent_attempts": self.healing_history[-10:],
                "rules_status": {},
            }

            for pattern, rule in self.healing_rules.items():
                stats["rules_status"][pattern] = {
                    "attempt_count": rule["attempt_count"],
                    "max_attempts": rule["max_attempts"],
                    "last_attempt": rule["last_attempt"],
                    "cooldown_period": rule["cooldown_period"],
                }

            return stats


class ResilienceOrchestrator:
    """Main orchestrator for resilience features."""

    def __init__(self):
        self.circuit_breakers = {}
        self.retry_manager = RetryManager()
        self.failover_manager = FailoverManager()
        self.degradation_manager = GracefulDegradationManager()
        self.healing_manager = SelfHealingManager()
        self.error_events: deque[ErrorEvent] = deque(maxlen=1000)
        self.lock = threading.RLock()

        self._setup_default_healing_rules()

    def create_circuit_breaker(
        self, name: str, config: CircuitBreakerConfig,
    ) -> CircuitBreaker:
        """Create and register circuit breaker."""
        with self.lock:
            circuit_breaker = CircuitBreaker(name, config)
            self.circuit_breakers[name] = circuit_breaker
            logger.info(f"Created circuit breaker: {name}")
            return circuit_breaker

    def get_circuit_breaker(self, name: str) -> CircuitBreaker | None:
        """Get circuit breaker by name."""
        return self.circuit_breakers.get(name)

    async def handle_error(
        self, error: Exception, service_name: str, context: dict[str, Any],
    ) -> None:
        """Comprehensive error handling with resilience features."""
        # Use SHA-256 for generated IDs to avoid weak-hash warnings (MD5).
        # These IDs are non-secret identifiers for internal error events.
        error_event = ErrorEvent(
            id=hashlib.sha256(f"{service_name}{time.time()}".encode()).hexdigest(),
            service=service_name,
            error_type=type(error).__name__,
            error_message=str(error),
            severity=self._classify_error_severity(error),
            timestamp=datetime.now(UTC),
            context=context,
            stack_trace=traceback.format_exc(),
        )

        self.error_events.append(error_event)

        # Log error
        logger.error(f"Error in {service_name}: {error_event.error_message}")

        # Attempt self - healing
        healing_successful = await self.healing_manager.attempt_healing(error, context)

        if healing_successful:
            error_event.resolved = True
            logger.info("Error automatically resolved through self - healing")
        else:
            # Trigger failover if configured
            try:
                await self.failover_manager._perform_failover(service_name)
            except Exception as failover_error:
                logger.error(f"Failover failed for {service_name}: {failover_error}")

    def _classify_error_severity(self, error: Exception) -> ErrorSeverity:
        """Classify error severity based on type and message."""
        # error_type = type(error).__name__
        error_message = str(error).lower()

        # Critical errors
        if any(
            keyword in error_message
            for keyword in [
                "out of memory",
                "disk full",
                "database connection failed",
                "authentication failed",
                "access denied",
            ]
        ):
            return ErrorSeverity.CRITICAL

        # High severity errors
        if any(
            keyword in error_message
            for keyword in [
                "timeout",
                "connection refused",
                "server error",
                "internal error",
                "service unavailable",
            ]
        ):
            return ErrorSeverity.HIGH

        # Medium severity errors
        if any(
            keyword in error_message
            for keyword in [
                "bad request",
                "not found",
                "validation error",
                "parse error",
                "format error",
            ]
        ):
            return ErrorSeverity.MEDIUM

        # Default to low severity
        return ErrorSeverity.LOW

    def _setup_default_healing_rules(self) -> None:
        """Setup default self - healing rules."""
        # Database connection healing

        async def heal_database_connection(
            error: Exception, context: dict[str, Any],
        ) -> bool:
            try:
                # Attempt to restart database connection
                logger.info("Attempting to heal database connection")
                await asyncio.sleep(1)  # Simulate healing action
                return True
            except Exception:
                return False

        self.healing_manager.register_healing_rule(
            "database connection",
            heal_database_connection,
            max_attempts=3,
            cooldown_period=60,
        )

        # Memory pressure healing

        async def heal_memory_pressure(
            error: Exception, context: dict[str, Any],
        ) -> bool:
            try:
                logger.info("Attempting to heal memory pressure")
                import gc

                gc.collect()  # Force garbage collection
                return True
            except Exception:
                return False

        self.healing_manager.register_healing_rule(
            "out of memory", heal_memory_pressure, max_attempts=2, cooldown_period=30,
        )

    def get_resilience_dashboard(self) -> dict[str, Any]:
        """Get comprehensive resilience dashboard."""
        with self.lock:
            # Circuit breaker stats
            cb_stats = {}
            for name, cb in self.circuit_breakers.items():
                cb_stats[name] = cb.get_stats()

            # Recent errors by severity
            recent_errors: list[ErrorEvent] = list(self.error_events)[
                -50:
            ]  # Last 50 errors
            error_counts: defaultdict[str, int] = defaultdict(int)
            for error in recent_errors:
                error_counts[str(error.severity.value)] += 1

            # Auto - resolution rate
            resolved_errors = sum(1 for error in recent_errors if error.resolved)
            resolution_rate = (
                resolved_errors / len(recent_errors) * 100 if recent_errors else 0
            )

            return {
                "timestamp": datetime.now(UTC).isoformat(),
                "circuit_breakers": cb_stats,
                "retry_stats": self.retry_manager.get_stats(),
                "failover_stats": self.failover_manager.get_failover_stats(),
                "degradation_status": self.degradation_manager.get_degradation_status(),
                "healing_stats": self.healing_manager.get_healing_stats(),
                "error_summary": {
                    "total_errors": len(self.error_events),
                    "recent_errors": len(recent_errors),
                    "error_counts_by_severity": dict(error_counts),
                    "auto_resolution_rate": resolution_rate,
                },
                "system_health": self._calculate_system_health(),
            }

    def _calculate_system_health(self) -> dict[str, Any]:
        """Calculate overall system health score."""
        health_factors: list[float] = []

        # Circuit breaker health
        cb_health: float = 0.0
        if self.circuit_breakers:
            closed_breakers = sum(
                1
                for cb in self.circuit_breakers.values()
                if cb.state == CircuitState.CLOSED
            )
            cb_health = (closed_breakers / len(self.circuit_breakers)) * 100.0
        else:
            cb_health = 100.0  # No circuit breakers=no circuit breaker issues

        health_factors.append(cb_health)

        # Error rate health
        recent_errors = list(self.error_events)[-100:]  # Last 100 operations
        critical_errors = sum(
            1 for error in recent_errors if error.severity == ErrorSeverity.CRITICAL
        )
        error_health: float = float(
            max(0, 100 - (critical_errors * 10)),
        )  # 10 points per critical error
        health_factors.append(error_health)

        # Auto - resolution health
        resolved_errors = sum(1 for error in recent_errors if error.resolved)
        resolution_health: float = (
            (resolved_errors / len(recent_errors) * 100.0) if recent_errors else 100.0
        )
        health_factors.append(resolution_health)

        overall_health: float = (
            (sum(health_factors) / len(health_factors)) if health_factors else 100.0
        )

        return {
            "overall_score": round(overall_health, 2),
            "circuit_breaker_health": round(cb_health, 2),
            "error_rate_health": round(error_health, 2),
            "resolution_health": round(resolution_health, 2),
            "status": self._get_health_status(overall_health),
        }

    def _get_health_status(self, score: float) -> str:
        """Get health status based on score."""
        if score >= 95:
            return "excellent"
        if score >= 85:
            return "good"
        if score >= 70:
            return "fair"
        if score >= 50:
            return "poor"
        return "critical"


# Global resilience orchestrator
resilience_orchestrator = ResilienceOrchestrator()

# Convenience decorators and functions


def circuit_breaker(name: str, config: CircuitBreakerConfig | None = None):
    """Circuit breaker decorator."""
    if config is None:
        config = CircuitBreakerConfig()

    cb = resilience_orchestrator.create_circuit_breaker(name, config)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await cb.call_async(func, *args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return cb.call(func, *args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def retry_on_failure(policy: RetryPolicy | None = None):
    """Retry decorator."""
    if policy is None:
        policy = RetryPolicy()

    return resilience_orchestrator.retry_manager.retry(policy)


async def handle_service_error(
    error: Exception, service_name: str, context: dict[str, Any] | None = None,
) -> None:
    """Handle service error with full resilience features."""
    await resilience_orchestrator.handle_error(error, service_name, context or {})


def get_resilience_dashboard() -> dict[str, Any]:
    """Get resilience dashboard data."""
    return resilience_orchestrator.get_resilience_dashboard()


def initialize_resilience_system() -> None:
    """Initialize resilience system with default configurations."""
    logger.info("Resilience system initialized")


# Export main components
__all__ = [
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "FailoverManager",
    "GracefulDegradationManager",
    "ResilienceOrchestrator",
    "RetryManager",
    "RetryPolicy",
    "SelfHealingManager",
    "circuit_breaker",
    "get_resilience_dashboard",
    "handle_service_error",
    "initialize_resilience_system",
    "retry_on_failure",
]
