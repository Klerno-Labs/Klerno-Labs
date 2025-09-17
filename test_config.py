# Test Configuration and Fixtures
"""
Test configuration module providing fixtures and utilities for the comprehensive test suite.
"""

import pytest
import asyncio
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, Optional, Generator
import logging

# Add project root to Python path for imports
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "app"))

# Test configuration
TEST_CONFIG = {
    "database": {
        "url": "sqlite:///test_klerno.db",
        "echo": False
    },
    "performance": {
        "cache_size": 100,
        "timeout_seconds": 5,
        "max_concurrent_requests": 10
    },
    "security": {
        "threat_threshold": 5,
        "block_threshold": 10,
        "analysis_window_minutes": 5
    },
    "memory": {
        "cache_limit_mb": 10,
        "pool_size": 5,
        "gc_interval_seconds": 10
    },
    "observability": {
        "sampling_rate": 1.0,
        "metrics_interval": 1,
        "trace_retention": 100
    },
    "resilience": {
        "circuit_breaker_threshold": 3,
        "recovery_timeout": 5,
        "health_check_interval": 10
    }
}


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment before each test."""
    # Set test configuration
    os.environ["TESTING"] = "true"
    os.environ["LOG_LEVEL"] = "ERROR"
    os.environ["ENVIRONMENT"] = "test"
    
    # Disable external connections in tests
    os.environ["DISABLE_EXTERNAL_CONNECTIONS"] = "true"
    
    yield
    
    # Cleanup after test
    cleanup_vars = ["TESTING", "LOG_LEVEL", "ENVIRONMENT", "DISABLE_EXTERNAL_CONNECTIONS"]
    for var in cleanup_vars:
        if var in os.environ:
            del os.environ[var]


@pytest.fixture
def test_config():
    """Provide test configuration."""
    return TEST_CONFIG.copy()


@pytest.fixture
def temp_directory():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_database():
    """Mock database connection for testing."""
    with patch('app.core.database.create_engine') as mock_engine:
        mock_conn = Mock()
        mock_engine.return_value.connect.return_value = mock_conn
        yield mock_conn


@pytest.fixture
def mock_redis():
    """Mock Redis connection for testing."""
    with patch('redis.Redis') as mock_redis:
        mock_client = Mock()
        mock_redis.return_value = mock_client
        yield mock_client


@pytest.fixture
def sample_request_data():
    """Provide sample HTTP request data for testing."""
    return {
        "method": "GET",
        "path": "/api/test",
        "headers": {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 Test Browser",
            "X-Forwarded-For": "192.168.1.100"
        },
        "body": {"test": "data"},
        "client_ip": "192.168.1.100",
        "timestamp": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def sample_security_threat():
    """Provide sample security threat data."""
    return {
        "type": "sql_injection",
        "source_ip": "192.168.1.200",
        "severity": "high",
        "payload": "'; DROP TABLE users; --",
        "timestamp": "2024-01-01T00:00:00Z",
        "user_agent": "malicious-bot/1.0"
    }


@pytest.fixture
def sample_performance_metrics():
    """Provide sample performance metrics."""
    return {
        "response_time": 150.5,
        "memory_usage": 512.7,
        "cpu_usage": 45.2,
        "cache_hit_rate": 0.85,
        "active_connections": 25,
        "requests_per_second": 120.3
    }


@pytest.fixture
def mock_performance_optimizer():
    """Mock performance optimizer for testing."""
    mock_optimizer = Mock()
    mock_optimizer.analyze_code_file = AsyncMock()
    mock_optimizer.optimize_async_call = AsyncMock()
    mock_optimizer.cache_put = AsyncMock(return_value=True)
    mock_optimizer.cache_get = AsyncMock(return_value=None)
    mock_optimizer.get_cache_metrics = Mock(return_value={
        "hit_rate": 0.85,
        "size": 100,
        "hits": 85,
        "misses": 15
    })
    return mock_optimizer


@pytest.fixture
def mock_security_monitor():
    """Mock security monitor for testing."""
    mock_monitor = Mock()
    mock_monitor.analyze_request = AsyncMock(return_value={
        "threat_level": "low",
        "recommendations": [],
        "block_request": False
    })
    mock_monitor.handle_security_incident = Mock()
    mock_monitor.get_comprehensive_metrics = Mock(return_value={
        "threats_detected": {"total": 0},
        "requests_blocked": {"total": 0},
        "incidents": {"total": 0}
    })
    return mock_monitor


@pytest.fixture
def mock_resilience_orchestrator():
    """Mock resilience orchestrator for testing."""
    mock_orchestrator = Mock()
    mock_orchestrator.execute_with_resilience = AsyncMock()
    mock_orchestrator.predict_service_failure = AsyncMock(return_value={
        "failure_probability": 0.1,
        "recommended_actions": []
    })
    mock_orchestrator.execute_recovery_procedure = AsyncMock(return_value={
        "success": True,
        "actions_taken": ["restart_service"],
        "recovery_time": 30
    })
    return mock_orchestrator


@pytest.fixture
def mock_memory_optimizer():
    """Mock memory optimizer for testing."""
    mock_optimizer = Mock()
    mock_optimizer.create_cache = Mock()
    mock_optimizer.create_memory_pool = Mock()
    mock_optimizer.gc_optimizer = Mock()
    mock_optimizer.resource_processor = Mock()
    return mock_optimizer


@pytest.fixture
def mock_observability_manager():
    """Mock observability manager for testing."""
    mock_manager = Mock()
    mock_manager.tracer = Mock()
    mock_manager.metrics = Mock()
    mock_manager.alerts = Mock()
    mock_manager.profiler = Mock()
    return mock_manager


@pytest.fixture
def disable_logging():
    """Disable logging during tests to reduce noise."""
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


class TestUtilities:
    """Utility functions for testing."""
    
    @staticmethod
    def create_test_file(directory: Path, filename: str, content: str) -> Path:
        """Create a test file with specified content."""
        file_path = directory / filename
        file_path.write_text(content)
        return file_path
    
    @staticmethod
    def assert_dict_contains(actual: Dict[str, Any], expected: Dict[str, Any]) -> None:
        """Assert that actual dictionary contains all expected key-value pairs."""
        for key, value in expected.items():
            assert key in actual, f"Key '{key}' not found in actual dict"
            assert actual[key] == value, f"Expected {key}={value}, got {actual[key]}"
    
    @staticmethod
    def assert_performance_metrics(metrics: Dict[str, Any], thresholds: Dict[str, float]) -> None:
        """Assert that performance metrics meet specified thresholds."""
        for metric, threshold in thresholds.items():
            assert metric in metrics, f"Metric '{metric}' not found"
            assert metrics[metric] <= threshold, f"Metric '{metric}' ({metrics[metric]}) exceeds threshold ({threshold})"
    
    @staticmethod
    async def wait_for_condition(condition_func, timeout: float = 5.0, interval: float = 0.1) -> bool:
        """Wait for a condition to become true with timeout."""
        import asyncio
        import time
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if await condition_func() if asyncio.iscoroutinefunction(condition_func) else condition_func():
                return True
            await asyncio.sleep(interval)
        return False


# Export test utilities
test_utils = TestUtilities()