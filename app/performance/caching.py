from typing import Any


class SimpleCache:
    async def get(self, key: str) -> Any | None:
        return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        return None


# Expose a default cache instance so callers can import `cache`.
cache = SimpleCache()
