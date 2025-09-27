"""
Advanced Caching System
Multi-tier caching with Redis, in-memory cache, and intelligent cache strategies
"""

import asyncio
import hashlib
import json
import pickle
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from typing import Any

import redis.asyncio as redis


@dataclass
class CacheEntry:
    """Cache entry with metadata"""

    value: Any
    timestamp: datetime
    ttl: int | None = None
    access_count: int = 0
    last_accessed: datetime | None = None

    def __post_init__(self):
        if self.last_accessed is None:
            self.last_accessed = self.timestamp

    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.ttl is None:
            return False
        return (datetime.utcnow() - self.timestamp).total_seconds() > self.ttl

    def access(self):
        """Record cache access"""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()


class InMemoryCache:
    """High-performance in-memory cache with LRU eviction"""

    def __init__(self, max_size: int = 10000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: dict[str, CacheEntry] = {}
        self.access_order: list[str] = []
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        """Get value from cache"""
        async with self._lock:
            if key not in self.cache:
                return None

            entry = self.cache[key]

            # Check expiration
            if entry.is_expired():
                await self._remove(key)
                return None

            # Update access order for LRU
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)

            entry.access()
            return entry.value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in cache"""
        async with self._lock:
            if ttl is None:
                ttl = self.default_ttl

            # Create cache entry
            entry = CacheEntry(value=value, timestamp=datetime.utcnow(), ttl=ttl)

            # Check if we need to evict
            if len(self.cache) >= self.max_size and key not in self.cache:
                await self._evict_lru()

            self.cache[key] = entry

            # Update access order
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        async with self._lock:
            return await self._remove(key)

    async def clear(self) -> None:
        """Clear all cache entries"""
        async with self._lock:
            self.cache.clear()
            self.access_order.clear()

    async def _remove(self, key: str) -> bool:
        """Remove key from cache (internal)"""
        if key in self.cache:
            del self.cache[key]
            if key in self.access_order:
                self.access_order.remove(key)
            return True
        return False

    async def _evict_lru(self) -> None:
        """Evict least recently used entry"""
        if self.access_order:
            lru_key = self.access_order[0]
            await self._remove(lru_key)

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics"""
        total_accesses = sum(entry.access_count for entry in self.cache.values())
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "total_accesses": total_accesses,
            "hit_rate": (
                0.0 if total_accesses == 0 else len(self.cache) / total_accesses
            ),
        }


class RedisCache:
    """Redis-based distributed cache"""

    def __init__(
        self, redis_url: str = "redis://localhost:6379", default_ttl: int = 3600
    ):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.redis_client: redis.Redis | None = None

    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=False)
            await self.redis_client.ping()
        except Exception as e:
            print(f"Redis connection failed: {e}")
            self.redis_client = None

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()

    async def get(self, key: str) -> Any | None:
        """Get value from Redis cache"""
        if not self.redis_client:
            return None

        try:
            data = await self.redis_client.get(key)
            if data:
                return pickle.loads(data)
        except Exception as e:
            print(f"Redis get error: {e}")

        return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set value in Redis cache"""
        if not self.redis_client:
            return False

        try:
            if ttl is None:
                ttl = self.default_ttl

            data = pickle.dumps(value)
            await self.redis_client.setex(key, ttl, data)
            return True
        except Exception as e:
            print(f"Redis set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from Redis cache"""
        if not self.redis_client:
            return False

        try:
            result = await self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            print(f"Redis delete error: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern"""
        if not self.redis_client:
            return 0

        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                return await self.redis_client.delete(*keys)
        except Exception as e:
            print(f"Redis clear pattern error: {e}")

        return 0


class MultiTierCache:
    """Multi-tier cache with in-memory L1 and Redis L2"""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        l1_max_size: int = 1000,
        default_ttl: int = 3600,
    ):
        self.l1_cache = InMemoryCache(max_size=l1_max_size, default_ttl=default_ttl)
        self.l2_cache = RedisCache(redis_url=redis_url, default_ttl=default_ttl)
        self.default_ttl = default_ttl

        # Cache statistics
        self.stats = {"l1_hits": 0, "l2_hits": 0, "misses": 0, "sets": 0}

    async def connect(self):
        """Initialize cache connections"""
        await self.l2_cache.connect()

    async def disconnect(self):
        """Close cache connections"""
        await self.l2_cache.disconnect()

    async def get(self, key: str) -> Any | None:
        """Get value from multi-tier cache"""
        # Try L1 cache first
        value = await self.l1_cache.get(key)
        if value is not None:
            self.stats["l1_hits"] += 1
            return value

        # Try L2 cache
        value = await self.l2_cache.get(key)
        if value is not None:
            self.stats["l2_hits"] += 1
            # Promote to L1 cache
            await self.l1_cache.set(key, value)
            return value

        self.stats["misses"] += 1
        return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in multi-tier cache"""
        if ttl is None:
            ttl = self.default_ttl

        # Set in both caches
        await self.l1_cache.set(key, value, ttl)
        await self.l2_cache.set(key, value, ttl)

        self.stats["sets"] += 1

    async def delete(self, key: str) -> bool:
        """Delete key from both cache tiers"""
        l1_deleted = await self.l1_cache.delete(key)
        l2_deleted = await self.l2_cache.delete(key)
        return l1_deleted or l2_deleted

    async def clear(self) -> None:
        """Clear both cache tiers"""
        await self.l1_cache.clear()
        # Note: We don't clear all of Redis, just our keys

    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive cache statistics"""
        total_requests = sum(
            [self.stats["l1_hits"], self.stats["l2_hits"], self.stats["misses"]]
        )

        l1_stats = self.l1_cache.get_stats()

        return {
            "total_requests": total_requests,
            "l1_hits": self.stats["l1_hits"],
            "l2_hits": self.stats["l2_hits"],
            "misses": self.stats["misses"],
            "sets": self.stats["sets"],
            "l1_hit_rate": (
                self.stats["l1_hits"] / total_requests if total_requests > 0 else 0
            ),
            "l2_hit_rate": (
                self.stats["l2_hits"] / total_requests if total_requests > 0 else 0
            ),
            "overall_hit_rate": (
                (self.stats["l1_hits"] + self.stats["l2_hits"]) / total_requests
                if total_requests > 0
                else 0
            ),
            "l1_cache_stats": l1_stats,
        }


# Global cache instances
cache = MultiTierCache()


def cache_key(*args, **kwargs) -> str:
    """Generate cache key from arguments"""
    key_data = {"args": args, "kwargs": sorted(kwargs.items())}
    key_string = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_string.encode()).hexdigest()


def cached(ttl: int = 3600, key_prefix: str = ""):
    """Decorator for caching function results"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key = f"{key_prefix}:{func.__name__}:{cache_key(*args, **kwargs)}"

            # Try to get from cache
            cached_result = await cache.get(key)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(key, result, ttl)

            return result

        return wrapper

    return decorator


@asynccontextmanager
async def cache_context():
    """Context manager for cache lifecycle"""
    await cache.connect()
    try:
        yield cache
    finally:
        await cache.disconnect()


# Specific cache functions for common use cases
@cached(ttl=300, key_prefix="user")
async def get_user_by_id(user_id: int):
    """Cached user lookup by ID"""
    # This would be implemented in your user service
    pass


@cached(ttl=600, key_prefix="compliance")
async def get_compliance_tags(transaction_id: int):
    """Cached compliance tags lookup"""
    # This would be implemented in your compliance service
    pass


@cached(ttl=1800, key_prefix="analytics")
async def get_user_analytics(user_id: int, date_range: str):
    """Cached user analytics"""
    # This would be implemented in your analytics service
    pass
