"""
Test cases for resilience system components.
"""
import pytest
import time
from app.resilience_system import (
    CircuitBreaker,
        CircuitBreakerConfig,
        CircuitState,
        CircuitBreakerOpenError,
        )


def test_circuit_breaker_closed_to_open():
    """Test circuit breaker transitions from CLOSED to OPEN when failure threshold is reached."""
    config=CircuitBreakerConfig(failure_threshold=2, timeout_duration=1.0)
    cb=CircuitBreaker("test_service", config)

    # Initially closed
    assert cb.state == CircuitState.CLOSED


    def failing_function():
        raise Exception("Service failure")

    # First failure - should remain closed
    with pytest.raises(Exception):
        cb.call(failing_function)
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 1

    # Second failure - should open circuit
    with pytest.raises(Exception):
        cb.call(failing_function)
    assert cb.state == CircuitState.OPEN
    assert cb.failure_count == 2


def test_circuit_breaker_open_blocks_calls():
    """Test that circuit breaker blocks calls when open."""
    config=CircuitBreakerConfig(failure_threshold=1, timeout_duration=1.0)
    cb=CircuitBreaker("test_service", config)


    def failing_function():
        raise Exception("Service failure")

    # Trigger circuit to open
    with pytest.raises(Exception):
        cb.call(failing_function)
    assert cb.state == CircuitState.OPEN

    # Subsequent calls should be blocked
    with pytest.raises(CircuitBreakerOpenError):
        cb.call(lambda: "success")


def test_circuit_breaker_half_open_recovery():
    """Test circuit breaker recovery from OPEN to HALF_OPEN to CLOSED."""
    config=CircuitBreakerConfig(
        failure_threshold=1,
            success_threshold=2,
            timeout_duration=0.1  # Short timeout for testing
    )
    cb=CircuitBreaker("test_service", config)

    # Force circuit to open
    with pytest.raises(Exception):
        cb.call(lambda: exec('raise Exception("test")'))
    assert cb.state == CircuitState.OPEN

    # Wait for timeout
    time.sleep(0.2)

    # Next call should move to HALF_OPEN
    result=cb.call(lambda: "success1")
    assert result == "success1"
    assert cb.state == CircuitState.HALF_OPEN
    assert cb.success_count == 1

    # Another success should close the circuit
    result=cb.call(lambda: "success2")
    assert result == "success2"
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


def test_circuit_breaker_stats():
    """Test circuit breaker statistics tracking."""
    config=CircuitBreakerConfig(failure_threshold=2)
    cb=CircuitBreaker("test_service", config)

    # Make some calls
    cb.call(lambda: "success1")
    cb.call(lambda: "success2")

    try:
        cb.call(lambda: exec('raise Exception("failure")'))
    except Exception:
        pass

    stats=cb.get_stats()
    assert stats["name"] == "test_service"
    assert stats["state"] == CircuitState.CLOSED.value
    assert stats["total_requests"] == 3
    assert stats["total_failures"] == 1
    assert stats["failure_rate"] == 1 / 3
