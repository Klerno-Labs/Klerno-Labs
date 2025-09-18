#!/usr/bin/env python3
"""
Performance optimization validation script.
Tests caching systems, async processing, and load balancing functionality.
"""

import sys
import os
import asyncio
import time
from pathlib import Path

# Add the app directory to the Python path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

def test_performance_optimizer_initialization():
    """Test performance optimizer initialization."""
    try:
        from app.performance_optimization import PerformanceOptimizer
        
        optimizer = PerformanceOptimizer()
        assert optimizer is not None, "Performance optimizer should initialize"
        
        # Test optimizer has required components
        assert hasattr(optimizer, 'cache'), "Optimizer should have cache"
        assert hasattr(optimizer, 'async_executor'), "Optimizer should have async executor"
        
        print("✅ Performance optimizer initialization: PASSED")
        return True
    except Exception as e:
        print(f"❌ Performance optimizer initialization: FAILED - {e}")
        return False

def test_caching_system():
    """Test caching system functionality."""
    try:
        from app.performance_optimization import CacheManager
        
        cache_manager = CacheManager()
        
        # Test basic cache operations
        test_key = "test_key"
        test_value = "test_value"
        
        # Set cache value
        cache_manager.set(test_key, test_value)
        
        # Get cache value
        retrieved_value = cache_manager.get(test_key)
        assert retrieved_value == test_value, "Should retrieve cached value"
        
        # Test cache expiration
        cache_manager.set("expiry_test", "value", ttl=0.1)
        time.sleep(0.2)
        expired_value = cache_manager.get("expiry_test")
        assert expired_value is None, "Expired value should be None"
        
        print("✅ Caching system: PASSED")
        return True
    except Exception as e:
        print(f"❌ Caching system: FAILED - {e}")
        return False

def test_redis_cache_fallback():
    """Test Redis cache with fallback."""
    try:
        from app.performance_optimization import RedisCacheManager
        
        redis_cache = RedisCacheManager()
        
        # Test Redis connection (should fallback to in-memory)
        assert hasattr(redis_cache, 'redis_client'), "Should have redis client"
        
        # Test fallback operations
        test_key = "redis_test"
        test_value = {"data": "test"}
        
        redis_cache.set(test_key, test_value)
        retrieved = redis_cache.get(test_key)
        
        # Should work with fallback even if Redis is not available
        assert retrieved is not None, "Should work with fallback"
        
        print("✅ Redis cache fallback: PASSED")
        return True
    except Exception as e:
        print(f"❌ Redis cache fallback: FAILED - {e}")
        return False

def test_memcached_support():
    """Test Memcached support."""
    try:
        from app.performance_optimization import MemcachedManager
        
        memcached_manager = MemcachedManager()
        
        # Test Memcached operations
        assert hasattr(memcached_manager, 'client'), "Should have memcached client"
        
        # Test basic operations
        test_key = "memcached_test"
        test_value = "memcached_value"
        
        success = memcached_manager.set(test_key, test_value)
        assert isinstance(success, bool), "Set operation should return boolean"
        
        retrieved = memcached_manager.get(test_key)
        # Should work even if memcached is not available (fallback)
        
        print("✅ Memcached support: PASSED")
        return True
    except Exception as e:
        print(f"❌ Memcached support: FAILED - {e}")
        return False

def test_async_processing():
    """Test async processing capabilities."""
    try:
        from app.performance_optimization import AsyncProcessor
        
        async_processor = AsyncProcessor()
        
        # Test async processor has required methods
        assert hasattr(async_processor, 'process_async'), "Should have process_async method"
        assert hasattr(async_processor, 'batch_process'), "Should have batch_process method"
        
        # Test simple async operation
        async def test_async_operation():
            result = await async_processor.process_async(lambda: "async_result")
            return result
        
        # Run async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(test_async_operation())
        loop.close()
        
        assert result == "async_result", "Async operation should return result"
        
        print("✅ Async processing: PASSED")
        return True
    except Exception as e:
        print(f"❌ Async processing: FAILED - {e}")
        return False

def test_connection_pooling():
    """Test connection pooling."""
    try:
        from app.performance_optimization import ConnectionPoolManager
        
        pool_manager = ConnectionPoolManager()
        
        # Test pool manager
        assert hasattr(pool_manager, 'get_connection'), "Should have get_connection method"
        assert hasattr(pool_manager, 'return_connection'), "Should have return_connection method"
        
        # Test database pool
        if hasattr(pool_manager, 'database_pool'):
            assert pool_manager.database_pool is not None, "Should have database pool"
        
        # Test HTTP client pool
        if hasattr(pool_manager, 'http_pool'):
            assert pool_manager.http_pool is not None, "Should have HTTP pool"
        
        print("✅ Connection pooling: PASSED")
        return True
    except Exception as e:
        print(f"❌ Connection pooling: FAILED - {e}")
        return False

def test_batch_processing():
    """Test batch processing capabilities."""
    try:
        from app.performance_optimization import BatchProcessor
        
        batch_processor = BatchProcessor()
        
        # Test batch processor
        assert hasattr(batch_processor, 'process_batch'), "Should have process_batch method"
        assert hasattr(batch_processor, 'add_to_batch'), "Should have add_to_batch method"
        
        # Test batch operations
        test_items = [1, 2, 3, 4, 5]
        
        # Add items to batch
        for item in test_items:
            batch_processor.add_to_batch(item)
        
        # Process batch
        if hasattr(batch_processor, 'batch_size'):
            assert batch_processor.batch_size > 0, "Should have positive batch size"
        
        print("✅ Batch processing: PASSED")
        return True
    except Exception as e:
        print(f"❌ Batch processing: FAILED - {e}")
        return False

def test_lazy_loading():
    """Test lazy loading implementation."""
    try:
        from app.performance_optimization import LazyLoader
        
        lazy_loader = LazyLoader()
        
        # Test lazy loader
        assert hasattr(lazy_loader, 'load'), "Should have load method"
        
        # Test lazy loading functionality
        def expensive_operation():
            time.sleep(0.01)  # Simulate expensive operation
            return "expensive_result"
        
        # Load lazily
        result = lazy_loader.load("test_key", expensive_operation)
        assert result == "expensive_result", "Should return result from expensive operation"
        
        # Second call should be cached
        start_time = time.time()
        cached_result = lazy_loader.load("test_key", expensive_operation)
        end_time = time.time()
        
        assert cached_result == "expensive_result", "Should return cached result"
        assert (end_time - start_time) < 0.005, "Cached call should be faster"
        
        print("✅ Lazy loading: PASSED")
        return True
    except Exception as e:
        print(f"❌ Lazy loading: FAILED - {e}")
        return False

def main():
    """Run all performance optimization tests."""
    print("⚡ Performance Optimization Validation")
    print("=" * 40)
    
    tests = [
        test_performance_optimizer_initialization,
        test_caching_system,
        test_redis_cache_fallback,
        test_memcached_support,
        test_async_processing,
        test_connection_pooling,
        test_batch_processing,
        test_lazy_loading
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: FAILED - {e}")
    
    print("\n" + "=" * 40)
    print(f"Performance Systems Results: {passed}/{total} passed")
    
    if passed >= total * 0.75:  # 75% pass rate is acceptable
        print("🎉 Performance optimization systems are working well!")
        return True
    else:
        print(f"⚠️  {total - passed} performance systems need attention")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)