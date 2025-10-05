#!/usr/bin/env python3
"""Rate limiting implementation for FastAPI."""

import logging
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


class RateLimiter:
    """In-memory rate limiter with sliding window."""

    def __init__(
        self, requests_per_window: int = 100, window_seconds: int = 60
    ) -> None:
        """Initialize rate limiter."""
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.requests: dict[str, deque] = defaultdict(lambda: deque())

    def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed for the given identifier."""
        current_time = time.time()
        request_times = self.requests[identifier]

        # Remove old requests outside the window
        while request_times and request_times[0] < current_time - self.window_seconds:
            request_times.popleft()

        # Check if under the limit
        if len(request_times) < self.requests_per_window:
            request_times.append(current_time)
            return True

        return False

    def get_remaining_requests(self, identifier: str) -> int:
        """Get remaining requests for the identifier."""
        current_time = time.time()
        request_times = self.requests[identifier]

        # Remove old requests
        while request_times and request_times[0] < current_time - self.window_seconds:
            request_times.popleft()

        return max(0, self.requests_per_window - len(request_times))

    def get_reset_time(self, identifier: str) -> float:
        """Get when the rate limit resets for the identifier."""
        request_times = self.requests[identifier]

        if not request_times:
            return time.time()

        return request_times[0] + self.window_seconds


class RateLimitMiddleware:
    """Rate limiting middleware for FastAPI."""

    def __init__(
        self, requests_per_window: int = 100, window_seconds: int = 60
    ) -> None:
        """Initialize rate limit middleware."""
        self.rate_limiter = RateLimiter(requests_per_window, window_seconds)

    def get_client_identifier(self, request: Request) -> str:
        """Get unique identifier for rate limiting."""
        # Try to get real IP from proxy headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Get first IP from the chain
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        # Include user agent for additional uniqueness
        user_agent = request.headers.get("User-Agent", "")[:50]  # First 50 chars

        return f"{client_ip}:{hash(user_agent)}"

    def check_rate_limit(self, request: Request) -> None:
        """Check rate limit and raise exception if exceeded."""
        identifier = self.get_client_identifier(request)

        if not self.rate_limiter.is_allowed(identifier):
            remaining = self.rate_limiter.get_remaining_requests(identifier)
            reset_time = self.rate_limiter.get_reset_time(identifier)

            logger.warning(f"Rate limit exceeded for {identifier}")

            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please try again later.",
                    "remaining_requests": remaining,
                    "reset_time": reset_time,
                    "retry_after": int(reset_time - time.time()),
                },
                headers={
                    "Retry-After": str(int(reset_time - time.time())),
                    "X-RateLimit-Limit": str(self.rate_limiter.requests_per_window),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(int(reset_time)),
                },
            )


# Global rate limiter instances
default_rate_limiter = RateLimitMiddleware(requests_per_window=100, window_seconds=60)
strict_rate_limiter = RateLimitMiddleware(requests_per_window=10, window_seconds=60)


def rate_limit(requests_per_window: int = 100, window_seconds: int = 60):
    """Decorator for rate limiting specific endpoints."""
    limiter = RateLimitMiddleware(requests_per_window, window_seconds)

    def decorator(func):
        def wrapper(request: Request, *args, **kwargs):
            limiter.check_rate_limit(request)
            return func(request, *args, **kwargs)

        return wrapper

    return decorator


# Example usage:
# from rate_limiting import rate_limit, default_rate_limiter
#
# @app.middleware("http")
# async def rate_limit_middleware(request: Request, call_next):
#     default_rate_limiter.check_rate_limit(request)
#     response = await call_next(request)
#     return response
#
# @app.post("/api/sensitive")
# @rate_limit(requests_per_window=10, window_seconds=60)
# async def sensitive_endpoint(request: Request):
#     return {"message": "Success"}
