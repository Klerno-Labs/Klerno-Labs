"""Test cases for performance optimization components."""

import asyncio

import pytest

from app.performance_consolidated import cached


def test_cached_decorator_basic():
    """Test that cached decorator caches return values."""
    call_count = 0

    @cached(ttl=60, max_size=100)
    def expensive_function(x, y):
        nonlocal call_count
        call_count += 1
        return x + y

    # First call should execute function
    result1 = expensive_function(1, 2)
    assert result1 == 3
    assert call_count == 1

    # Second call with same args should return cached value
    result2 = expensive_function(1, 2)
    assert result2 == 3
    assert call_count == 1  # Function not called again

    # Call with different args should execute function
    result3 = expensive_function(2, 3)
    assert result3 == 5
    assert call_count == 2


def test_cached_decorator_with_kwargs():
    """Test cached decorator works with keyword arguments."""
    call_count = 0

    @cached(ttl=60)
    def function_with_kwargs(a, b=10, c=20):
        nonlocal call_count
        call_count += 1
        return a + b + c

    # Same calls should be cached
    result1 = function_with_kwargs(1, b=10, c=20)
    result2 = function_with_kwargs(1, b=10, c=20)
    assert result1 == result2 == 31
    assert call_count == 1

    # Different kwargs should cause new execution
    result3 = function_with_kwargs(1, b=20, c=20)
    assert result3 == 41
    assert call_count == 2


@pytest.mark.asyncio
async def test_cached_decorator_async():
    """Test cached decorator works with async functions."""
    call_count = 0

    @cached(ttl=60)
    async def async_expensive_function(x):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.001)  # Simulate async work
        return x * 2

    # First call
    result1 = await async_expensive_function(5)
    assert result1 == 10
    assert call_count == 1

    # Second call should be cached
    result2 = await async_expensive_function(5)
    assert result2 == 10
    assert call_count == 1


def test_cache_key_generation():
    """Test that cache keys are generated correctly for different argument patterns."""
    call_counts: dict[str, int] = {}

    @cached(ttl=60)
    def test_function(*args, **kwargs):
        key = str((args, tuple(sorted(kwargs.items()))))
        call_counts[key] = call_counts.get(key, 0) + 1
        return f"result_{key}"

    # Different argument combinations should generate different cache keys
    test_function(1, 2)
    test_function(1, 2)  # Same call - should be cached
    test_function(2, 1)  # Different order - different cache key
    test_function(1, 2, x=3)  # With kwargs

    # Verify each unique combination was called only once
    unique_calls = len([count for count in call_counts.values() if count == 1])
    assert unique_calls >= 3  # At least 3 different combinations
