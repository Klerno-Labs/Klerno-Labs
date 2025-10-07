"""Test for rate limit counters increment functionality."""

from unittest.mock import Mock

from app.middleware import RateLimitMiddleware


class TestRateLimitCountersIncrement:
    """Test rate limit counter increment behavior."""

    def test_rate_limit_counter_increments_correctly(self) -> None:
        """Test that rate limit counters increment properly."""
        middleware = RateLimitMiddleware(Mock(), requests_per_minute=5)
        current_time = 1000.0
        ip = "127.0.0.1"

        # Initially should not be rate limited
        assert not middleware._is_rate_limited(ip, current_time)

        # Record requests and verify counter increments
        for i in range(5):
            middleware._record_request(ip, current_time + i)

        # Should now be rate limited
        assert middleware._is_rate_limited(ip, current_time + 5)

    def test_rate_limit_cleanup_old_requests(self) -> None:
        """Test that old requests are cleaned up properly."""
        middleware = RateLimitMiddleware(Mock(), requests_per_minute=3)
        current_time = 1000.0
        ip = "127.0.0.1"

        # Add old requests
        middleware._record_request(ip, current_time - 120)  # 2 minutes ago
        middleware._record_request(ip, current_time - 30)  # 30 seconds ago
        middleware._record_request(ip, current_time)  # Now

        # Clean old requests
        middleware._clean_old_requests(current_time)

        # Should only have recent requests
        assert len(middleware.requests[ip]) == 2  # 30 seconds ago and now
