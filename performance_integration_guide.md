"""
Performance Optimization Integration Guide

This guide explains how to integrate the comprehensive performance optimization system
into your Klerno Labs FastAPI application for production-scale performance.

## Overview

The performance optimization system provides:
- ✅ Multi-tier caching (Redis + In-memory)
- ✅ Database connection pooling and optimization
- ✅ Advanced async patterns and concurrency control
- ✅ Performance middleware with monitoring
- ✅ Batch processing and task management
- ✅ Query optimization and indexing

## Files Created

### Core Performance Components
- `app/performance/caching.py` - Multi-tier caching system
- `app/performance/database.py` - Database optimization and pooling
- `app/performance/async_optimization.py` - Async patterns and concurrency
- `app/performance/middleware.py` - Performance middleware
- `app/performance/config.json` - Performance configuration

## Integration Steps

### 1. Install Performance Dependencies

Add to requirements.txt:
```
redis>=4.5.0
aioredis>=2.0.0
aiosqlite>=0.19.0
asyncpg>=0.28.0
aiocache>=0.12.0
```

Install:
```bash
pip install redis aioredis aiosqlite asyncpg aiocache
```

### 2. Initialize Performance Components in main.py

Add to the top of `app/main.py`:

```python
from app.performance.caching import cache_context
from app.performance.database import db_service
from app.performance.middleware import PerformanceMiddleware, AsyncOptimizationMiddleware
from app.performance.async_optimization import task_manager

# Add performance middleware
app.add_middleware(PerformanceMiddleware, cache_enabled=True, metrics_enabled=True)
app.add_middleware(AsyncOptimizationMiddleware, max_request_concurrency=100)
```

### 3. Setup Application Lifecycle

Add to `app/main.py`:

```python
@app.on_event("startup")
async def startup_event():
    # Initialize performance components
    await cache.connect()
    await db_service.start()

    logger.info("Performance optimization system initialized")

@app.on_event("shutdown")
async def shutdown_event():
    # Cleanup performance components
    await cache.disconnect()
    await db_service.stop()

    logger.info("Performance optimization system shutdown")
```

### 4. Configure Redis Connection

Set environment variables or update configuration:

```bash
# Redis configuration
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your_redis_password  # if needed
REDIS_DB=0

# Performance settings
MAX_DB_CONNECTIONS=20
CACHE_DEFAULT_TTL=3600
MAX_CONCURRENT_REQUESTS=100
```

### 5. Use Caching in Your Services

Update your service functions with caching:

```python
from app.performance.caching import cached, cache

# Cached user lookup
@cached(ttl=300, key_prefix="user")
async def get_user_by_id(user_id: int):
    # Your existing user lookup code
    pass

# Manual cache usage
async def get_user_analytics(user_id: int):
    cache_key = f"analytics:user:{user_id}"

    # Try cache first
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    # Compute analytics
    analytics_data = await compute_user_analytics(user_id)

    # Cache result
    await cache.set(cache_key, analytics_data, ttl=1800)

    return analytics_data
```

### 6. Use Optimized Database Service

Replace direct database calls with the optimized service:

```python
from app.performance.database import db_service

# Optimized user lookup with caching
async def get_user_by_id(user_id: int):
    return await db_service.get_user_by_id(user_id)

# Optimized transaction creation with compliance tags
async def create_transaction_with_analysis(transaction_data, compliance_tags):
    return await db_service.create_transaction_with_tags(transaction_data, compliance_tags)

# Get database performance stats
async def get_db_performance():
    return db_service.get_stats()
```

### 7. Use Async Optimization Patterns

Implement concurrent processing for improved performance:

```python
from app.performance.async_optimization import (
    task_manager, process_concurrent_tasks, batch_process_items,
    async_retry, async_timeout, async_rate_limit
)

# Process multiple transactions concurrently
@async_retry(max_retries=3)
@async_timeout(30.0)
async def process_bulk_transactions(transactions):
    # Create tasks for each transaction
    tasks = [process_single_transaction(tx) for tx in transactions]

    # Process with controlled concurrency
    results = await process_concurrent_tasks(tasks, max_concurrent=10)
    return results

# Batch process compliance analysis
async def analyze_transactions_batch(transaction_ids):
    async def analyze_single(tx_id):
        return await run_compliance_analysis(tx_id)

    return await batch_process_items(
        transaction_ids,
        analyze_single,
        batch_size=50,
        max_concurrent=10
    )

# Submit long-running task
async def submit_analytics_task(user_id, date_range):
    task_id = f"analytics:{user_id}:{date_range}"

    await task_manager.submit_task(
        task_id,
        compute_user_analytics_async(user_id, date_range),
        timeout=300.0
    )

    return task_id

# Get task result
async def get_analytics_result(task_id):
    return await task_manager.get_task_result(task_id)
```

## Performance Monitoring

### Cache Performance

```python
# Get cache statistics
async def get_cache_stats():
    return cache.get_stats()

# Example output:
{
    "total_requests": 10000,
    "l1_hits": 3000,
    "l2_hits": 5000,
    "misses": 2000,
    "l1_hit_rate": 0.3,
    "l2_hit_rate": 0.5,
    "overall_hit_rate": 0.8
}
```

### Database Performance

```python
# Get database performance statistics
async def get_db_stats():
    return db_service.get_stats()

# Example output:
{
    "connection_pool": {
        "total_connections": 15,
        "active_connections": 5,
        "idle_connections": 10,
        "total_queries": 50000,
        "avg_query_time": 0.025,
        "slow_queries": 23
    }
}
```

### Async Task Performance

```python
# Get task manager statistics
async def get_task_stats():
    return task_manager.get_stats()

# Example output:
{
    "total_tasks": 1000,
    "completed_tasks": 950,
    "failed_tasks": 25,
    "running_tasks": 25,
    "avg_execution_time": 2.5
}
```

## Performance Tuning

### Cache Configuration

```python
# Customize cache TTLs based on data volatility
cache_strategies = {
    "user_profiles": 300,      # 5 minutes (changes occasionally)
    "compliance_tags": 600,    # 10 minutes (computed data)
    "analytics_data": 1800,    # 30 minutes (expensive to compute)
    "static_content": 3600     # 1 hour (rarely changes)
}
```

### Database Optimization

```python
# Tune connection pool settings
connection_pool_config = {
    "max_connections": 20,           # Adjust based on load
    "max_idle_time": 300,           # 5 minutes idle timeout
    "slow_query_threshold": 1.0     # Log queries > 1 second
}
```

### Concurrency Settings

```python
# Adjust concurrency limits based on resources
concurrency_config = {
    "max_concurrent_requests": 100,  # HTTP request limit
    "max_concurrent_tasks": 50,      # Background task limit
    "batch_size": 50,               # Batch processing size
    "batch_timeout": 1.0            # Batch timeout seconds
}
```

## Production Deployment

### Redis Setup

```bash
# Install Redis
sudo apt-get install redis-server

# Configure Redis for production
# /etc/redis/redis.conf
maxmemory 256mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

### Monitoring Integration

Add performance monitoring endpoints:

```python
@app.get("/performance/stats")
async def get_performance_stats():
    return {
        "cache": await cache.get_stats(),
        "database": db_service.get_stats(),
        "tasks": task_manager.get_stats(),
        "timestamp": datetime.utcnow().isoformat()
    }
```

### Load Testing

```bash
# Test with Apache Bench
ab -n 1000 -c 10 http://localhost:8000/api/transactions

# Test with wrk
wrk -t4 -c100 -d30s http://localhost:8000/dashboard
```

## Performance Benchmarks

### Expected Improvements

| Metric | Before Optimization | After Optimization | Improvement |
|--------|-------------------|-------------------|-------------|
| Cache Hit Rate | 0% | 80%+ | ∞ |
| Database Query Time | 50-200ms | 5-25ms | 4-8x faster |
| Concurrent Users | 10-20 | 100+ | 5-10x more |
| Memory Usage | High | Optimized | 30-50% reduction |
| Response Time | 500ms-2s | 50-200ms | 5-10x faster |

### Performance Targets

- **Response Time**: < 200ms for 95% of requests
- **Cache Hit Rate**: > 80% for frequently accessed data
- **Database Queries**: < 50ms average query time
- **Concurrent Users**: Handle 100+ concurrent users
- **Memory Efficiency**: < 512MB RAM usage under normal load

## Troubleshooting

### Common Issues

1. **High Cache Miss Rate**
   - Check TTL settings
   - Verify cache key generation
   - Monitor cache eviction patterns

2. **Database Connection Exhaustion**
   - Increase max_connections
   - Check for connection leaks
   - Monitor query patterns

3. **High Response Times**
   - Enable slow query logging
   - Check concurrency limits
   - Profile database queries

4. **Memory Leaks**
   - Monitor cache size growth
   - Check async task cleanup
   - Review connection pooling

### Debug Mode

Enable performance debugging:

```python
import logging
logging.getLogger('app.performance').setLevel(logging.DEBUG)
```

## Next Steps

1. Monitor performance metrics in production
2. Set up alerting for performance degradation
3. Create performance dashboards
4. Implement automated performance testing
5. Regular performance optimization reviews
