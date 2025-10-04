
import functools
import time
from typing import Any, Dict, Optional

class ResponseCache:
    """Simple in-memory response cache with TTL."""
    
    def __init__(self, default_ttl: int = 300):  # 5 minutes default
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        
    def get(self, key: str) -> Optional[Any]:
        """Get cached response if not expired."""
        if key in self.cache:
            entry = self.cache[key]
            if time.time() < entry["expires_at"]:
                return entry["data"]
            else:
                del self.cache[key]
        return None
        
    def set(self, key: str, data: Any, ttl: Optional[int] = None) -> None:
        """Cache response with TTL."""
        ttl = ttl or self.default_ttl
        self.cache[key] = {
            "data": data,
            "expires_at": time.time() + ttl
        }
        
    def clear_expired(self) -> None:
        """Clear expired entries."""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if current_time >= entry["expires_at"]
        ]
        for key in expired_keys:
            del self.cache[key]

# Global cache instance
response_cache = ResponseCache()

def cached_response(ttl: int = 300):
    """Decorator for caching API responses."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and args
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached_result = response_cache.get(cache_key)
            if cached_result is not None:
                return cached_result
                
            # Execute function and cache result
            result = func(*args, **kwargs)
            response_cache.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator

# Usage example:
# @cached_response(ttl=60)  # Cache for 1 minute
# def health_check():
#     return {"status": "ok", "timestamp": time.time()}
