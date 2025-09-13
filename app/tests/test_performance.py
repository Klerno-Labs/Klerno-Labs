"""
Tests for performance optimization features.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch

from app.performance import (
    PerformanceMonitor, 
    PerformanceMetrics, 
    InMemoryCache,
    OptimizedLiveHub,
    performance_cache
)
from datetime import datetime


class TestPerformanceMonitor:
    """Test performance monitoring functionality."""
    
    def test_record_metric(self):
        monitor = PerformanceMonitor()
        metric = PerformanceMetrics(
            endpoint="/test",
            method="GET", 
            response_time_ms=50.0,
            status_code=200,
            timestamp=datetime.utcnow()
        )
        
        monitor.record_metric(metric)
        
        assert len(monitor.metrics) == 1
        stats = monitor.endpoint_stats["GET /test"]
        assert stats['count'] == 1
        assert stats['avg_time'] == 50.0
        assert stats['min_time'] == 50.0
        assert stats['max_time'] == 50.0
    
    def test_slow_endpoints_detection(self):
        monitor = PerformanceMonitor()
        
        # Add fast endpoint
        fast_metric = PerformanceMetrics(
            endpoint="/fast",
            method="GET",
            response_time_ms=30.0,
            status_code=200,
            timestamp=datetime.utcnow()
        )
        monitor.record_metric(fast_metric)
        
        # Add slow endpoint  
        slow_metric = PerformanceMetrics(
            endpoint="/slow", 
            method="POST",
            response_time_ms=150.0,
            status_code=200,
            timestamp=datetime.utcnow()
        )
        monitor.record_metric(slow_metric)
        
        slow_endpoints = monitor.get_slow_endpoints(100.0)
        assert len(slow_endpoints) == 1
        assert "POST /slow" in slow_endpoints
        assert "GET /fast" not in slow_endpoints
    
    def test_performance_summary(self):
        monitor = PerformanceMonitor()
        
        for i in range(5):
            metric = PerformanceMetrics(
                endpoint=f"/test{i}",
                method="GET",
                response_time_ms=50.0 + i * 10,
                status_code=200,
                timestamp=datetime.utcnow()
            )
            monitor.record_metric(metric)
        
        summary = monitor.get_summary()
        assert summary['total_requests'] == 5
        assert summary['recent_requests'] == 5
        assert summary['avg_response_time_ms'] == 70.0  # (50+60+70+80+90)/5
        assert summary['target_met'] is True  # Average is under 100ms


class TestInMemoryCache:
    """Test in-memory caching functionality."""
    
    def test_cache_set_get(self):
        cache = InMemoryCache()
        cache.set("test_key", "test_value", ttl=60)
        
        result = cache.get("test_key")
        assert result == "test_value"
    
    def test_cache_expiration(self):
        cache = InMemoryCache()
        cache.set("test_key", "test_value", ttl=1)
        
        # Should be available immediately
        assert cache.get("test_key") == "test_value"
        
        # Sleep longer than TTL
        time.sleep(1.1)
        
        # Should be expired
        assert cache.get("test_key") is None
    
    def test_cache_delete(self):
        cache = InMemoryCache()
        cache.set("test_key", "test_value")
        
        assert cache.delete("test_key") is True
        assert cache.get("test_key") is None
        assert cache.delete("non_existent") is False
    
    def test_cache_cleanup(self):
        cache = InMemoryCache()
        cache.set("keep", "value", ttl=60)
        cache.set("expire", "value", ttl=1)
        
        time.sleep(1.1)
        cleaned = cache.cleanup_expired()
        
        assert cleaned == 1
        assert cache.get("keep") == "value"
        assert cache.get("expire") is None


class TestPerformanceCache:
    """Test performance caching decorator."""
    
    def test_sync_function_caching(self):
        call_count = 0
        
        @performance_cache(ttl=60)
        def test_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        # First call
        result1 = test_function(5)
        assert result1 == 10
        assert call_count == 1
        
        # Second call with same argument should use cache
        result2 = test_function(5)
        assert result2 == 10
        assert call_count == 1  # Should not increment
        
        # Different argument should call function
        result3 = test_function(6)
        assert result3 == 12
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_async_function_caching(self):
        call_count = 0
        
        @performance_cache(ttl=60)
        async def async_test_function(x):
            nonlocal call_count
            call_count += 1
            return x * 3
        
        # First call
        result1 = await async_test_function(4)
        assert result1 == 12
        assert call_count == 1
        
        # Second call should use cache
        result2 = await async_test_function(4)
        assert result2 == 12
        assert call_count == 1


@pytest.mark.asyncio
class TestOptimizedLiveHub:
    """Test optimized WebSocket hub functionality."""
    
    async def test_add_remove_websocket(self):
        hub = OptimizedLiveHub()
        mock_ws = Mock()
        mock_ws.accept = Mock(return_value=asyncio.Future())
        mock_ws.accept.return_value.set_result(None)
        
        # Add WebSocket
        await hub.add(mock_ws)
        stats = hub.get_stats()
        assert stats['connections_active'] == 1
        
        # Remove WebSocket
        await hub.remove(mock_ws)
        stats = hub.get_stats()
        assert stats['connections_active'] == 0
    
    async def test_watch_update(self):
        hub = OptimizedLiveHub()
        mock_ws = Mock()
        mock_ws.accept = Mock(return_value=asyncio.Future())
        mock_ws.accept.return_value.set_result(None)
        
        await hub.add(mock_ws)
        
        # Update watch list
        watch_list = {"address1", "address2"}
        await hub.update_watch(mock_ws, watch_list)
        
        # Verify watch list was stored
        assert mock_ws in hub._clients
        assert hub._clients[mock_ws] == {"address1", "address2"}
    
    async def test_message_publishing(self):
        hub = OptimizedLiveHub()
        mock_ws = Mock()
        mock_ws.accept = Mock(return_value=asyncio.Future())
        mock_ws.accept.return_value.set_result(None)
        mock_ws.send_json = Mock(return_value=asyncio.Future())
        mock_ws.send_json.return_value.set_result(None)
        
        await hub.add(mock_ws)
        
        # Publish a message
        test_item = {
            "from_addr": "test_from",
            "to_addr": "test_to",
            "amount": 100
        }
        
        await hub.publish(test_item)
        
        # Give a moment for async processing
        await asyncio.sleep(0.1)
        
        stats = hub.get_stats()
        assert stats['messages_queued'] > 0


class TestPerformanceIntegration:
    """Integration tests for performance features."""
    
    def test_performance_metrics_with_cache(self):
        """Test that cache operations are fast and metrics are recorded."""
        cache = InMemoryCache()
        
        # Measure cache set performance
        start_time = time.perf_counter()
        for i in range(1000):
            cache.set(f"key_{i}", f"value_{i}")
        set_duration = (time.perf_counter() - start_time) * 1000  # Convert to ms
        
        # Should be very fast
        assert set_duration < 100  # Less than 100ms for 1000 operations
        
        # Measure cache get performance
        start_time = time.perf_counter()
        for i in range(1000):
            result = cache.get(f"key_{i}")
            assert result == f"value_{i}"
        get_duration = (time.perf_counter() - start_time) * 1000
        
        # Gets should be even faster
        assert get_duration < 50  # Less than 50ms for 1000 operations
    
    def test_endpoint_response_time_targeting(self):
        """Test that we can identify endpoints exceeding 100ms target."""
        monitor = PerformanceMonitor()
        
        # Simulate various endpoint response times
        endpoints_data = [
            ("/api/fast", 45.0),
            ("/api/medium", 85.0), 
            ("/api/slow", 120.0),
            ("/api/very_slow", 250.0),
            ("/api/acceptable", 95.0)
        ]
        
        for endpoint, response_time in endpoints_data:
            metric = PerformanceMetrics(
                endpoint=endpoint,
                method="GET",
                response_time_ms=response_time,
                status_code=200,
                timestamp=datetime.utcnow()
            )
            monitor.record_metric(metric)
        
        # Check which endpoints exceed 100ms target
        slow_endpoints = monitor.get_slow_endpoints(100.0)
        
        assert len(slow_endpoints) == 2
        assert "GET /api/slow" in slow_endpoints
        assert "GET /api/very_slow" in slow_endpoints
        assert "GET /api/fast" not in slow_endpoints
        assert "GET /api/medium" not in slow_endpoints
        assert "GET /api/acceptable" not in slow_endpoints
        
        # Verify that averages are calculated correctly
        assert slow_endpoints["GET /api/slow"]["avg_time"] == 120.0
        assert slow_endpoints["GET /api/very_slow"]["avg_time"] == 250.0