"""Async Performance Optimizations
Advanced async patterns, concurrency control, and performance improvements.
"""

import asyncio
import functools
import logging
import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ConcurrencyStats:
    """Concurrency performance statistics."""

    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    avg_completion_time: float = 0.0
    max_concurrent: int = 0
    current_concurrent: int = 0


class AsyncSemaphorePool:
    """Async semaphore pool for controlling concurrency."""

    def __init__(self, max_concurrent: int = 10) -> None:
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.stats = ConcurrencyStats(max_concurrent=max_concurrent)
        self.active_tasks: set = set()

    @asynccontextmanager
    async def acquire(self):
        """Acquire semaphore with statistics tracking."""
        await self.semaphore.acquire()

        task_id = id(asyncio.current_task())
        self.active_tasks.add(task_id)
        self.stats.current_concurrent = len(self.active_tasks)
        self.stats.total_tasks += 1

        start_time = time.time()

        try:
            yield

            # Update completion statistics
            completion_time = time.time() - start_time
            self.stats.completed_tasks += 1

            # Update average completion time
            current_avg = self.stats.avg_completion_time
            completed = self.stats.completed_tasks
            self.stats.avg_completion_time = (
                (current_avg * (completed - 1)) + completion_time
            ) / completed

        except Exception as e:
            self.stats.failed_tasks += 1
            logger.exception(f"Task failed: {e}")
            raise

        finally:
            self.active_tasks.discard(task_id)
            self.stats.current_concurrent = len(self.active_tasks)
            self.semaphore.release()


class BatchProcessor:
    """Batch processing for improved throughput."""

    def __init__(self, batch_size: int = 50, batch_timeout: float = 1.0) -> None:
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.pending_items: list[Any] = []
        self.batch_processors: dict[str, Callable] = {}
        self._processing_task: asyncio.Task | None = None
        self._shutdown = False

    def register_processor(
        self,
        name: str,
        processor: Callable[[list[Any]], Awaitable[list[Any]]],
    ) -> None:
        """Register a batch processor function."""
        self.batch_processors[name] = processor

    async def start(self) -> None:
        """Start batch processing."""
        if not self._processing_task:
            self._processing_task = asyncio.create_task(self._process_batches())

    async def stop(self) -> None:
        """Stop batch processing."""
        self._shutdown = True
        if self._processing_task:
            await self._processing_task

    async def add_item(self, item: Any) -> Any:
        """Add item to batch for processing."""
        future: asyncio.Future = asyncio.Future()
        self.pending_items.append((item, future))

        # Check if we should process immediately
        if len(self.pending_items) >= self.batch_size:
            await self._process_current_batch()

        return await future

    async def _process_batches(self) -> None:
        """Main batch processing loop."""
        while not self._shutdown:
            try:
                await asyncio.sleep(self.batch_timeout)

                if self.pending_items:
                    await self._process_current_batch()

            except Exception as e:
                logger.exception(f"Batch processing error: {e}")

    async def _process_current_batch(self) -> None:
        """Process current batch of items."""
        if not self.pending_items:
            return

        # Extract items and futures
        items = []
        futures = []

        batch_items = self.pending_items[: self.batch_size]
        self.pending_items = self.pending_items[self.batch_size :]

        for item, future in batch_items:
            items.append(item)
            futures.append(future)

        try:
            # Process batch (this would be customized for your use case)
            results = await self._default_processor(items)

            # Set results for futures
            for future, result in zip(futures, results, strict=False):
                if not future.done():
                    future.set_result(result)

        except Exception as e:
            # Set exception for all futures
            for future in futures:
                if not future.done():
                    future.set_exception(e)

    async def _default_processor(self, items: list[Any]) -> list[Any]:
        """Default batch processor (override for specific use cases)."""
        return items


class AsyncTaskManager:
    """Advanced async task management with monitoring."""

    def __init__(self, max_concurrent: int = 100) -> None:
        self.max_concurrent = max_concurrent
        self.semaphore_pool = AsyncSemaphorePool(max_concurrent)
        self.running_tasks: dict[str, asyncio.Task] = {}
        self.task_results: dict[str, Any] = {}
        self.task_stats: dict[str, dict[str, Any]] = {}

    async def submit_task(
        self,
        task_id: str,
        coro: Awaitable[Any],
        timeout: float | None = None,
    ) -> str:
        """Submit a task for async execution."""
        if task_id in self.running_tasks:
            msg = f"Task {task_id} is already running"
            raise ValueError(msg)

        async def _execute_task():
            start_time = time.time()

            try:
                async with self.semaphore_pool.acquire():
                    if timeout:
                        result = await asyncio.wait_for(coro, timeout=timeout)
                    else:
                        result = await coro

                    execution_time = time.time() - start_time

                    # Store result and stats
                    self.task_results[task_id] = result
                    self.task_stats[task_id] = {
                        "status": "completed",
                        "execution_time": execution_time,
                        "completed_at": datetime.utcnow().isoformat(),
                    }

                    return result

            except TimeoutError:
                execution_time = time.time() - start_time
                self.task_stats[task_id] = {
                    "status": "timeout",
                    "execution_time": execution_time,
                    "completed_at": datetime.utcnow().isoformat(),
                }
                raise

            except Exception as e:
                execution_time = time.time() - start_time
                self.task_stats[task_id] = {
                    "status": "failed",
                    "execution_time": execution_time,
                    "error": str(e),
                    "completed_at": datetime.utcnow().isoformat(),
                }
                raise

            finally:
                # Cleanup
                if task_id in self.running_tasks:
                    del self.running_tasks[task_id]

        # Create and store task
        task = asyncio.create_task(_execute_task())
        self.running_tasks[task_id] = task

        # Initialize stats
        self.task_stats[task_id] = {
            "status": "running",
            "started_at": datetime.utcnow().isoformat(),
        }

        return task_id

    async def get_task_result(self, task_id: str, wait: bool = True) -> Any:
        """Get task result."""
        if task_id in self.task_results:
            return self.task_results[task_id]

        if task_id in self.running_tasks and wait:
            task = self.running_tasks[task_id]
            return await task

        msg = f"Task {task_id} not found or not completed"
        raise ValueError(msg)

    def get_task_status(self, task_id: str) -> dict[str, Any]:
        """Get task status and statistics."""
        return self.task_stats.get(task_id, {"status": "not_found"})

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.cancel()

            self.task_stats[task_id] = {
                "status": "cancelled",
                "cancelled_at": datetime.utcnow().isoformat(),
            }

            return True

        return False

    def get_stats(self) -> dict[str, Any]:
        """Get task manager statistics."""
        total_tasks = len(self.task_stats)
        completed_tasks = sum(
            1 for stats in self.task_stats.values() if stats["status"] == "completed"
        )
        failed_tasks = sum(
            1 for stats in self.task_stats.values() if stats["status"] == "failed"
        )
        running_tasks = len(self.running_tasks)

        # Calculate average execution time for completed tasks
        completed_times = [
            stats.get("execution_time", 0)
            for stats in self.task_stats.values()
            if stats["status"] == "completed" and "execution_time" in stats
        ]
        avg_execution_time = (
            sum(completed_times) / len(completed_times) if completed_times else 0
        )

        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "running_tasks": running_tasks,
            "avg_execution_time": avg_execution_time,
            "concurrency_stats": {
                "max_concurrent": self.semaphore_pool.stats.max_concurrent,
                "current_concurrent": self.semaphore_pool.stats.current_concurrent,
                "total_tasks": self.semaphore_pool.stats.total_tasks,
                "completed_tasks": self.semaphore_pool.stats.completed_tasks,
                "failed_tasks": self.semaphore_pool.stats.failed_tasks,
                "avg_completion_time": self.semaphore_pool.stats.avg_completion_time,
            },
        }


def async_retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """Async retry decorator with exponential backoff."""

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.exception(
                            f"Function {func.__name__} failed after {max_retries} retries: {e}",
                        )
                        raise

                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt + 1}), retrying in {current_delay}s: {e}",
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff

            # Ensure we only raise an exception instance derived from BaseException
            if last_exception is not None:
                raise last_exception from None
            # Fallback: raise a generic RuntimeError if somehow no exception is captured
            msg = "Operation failed with unknown exception"
            raise RuntimeError(msg)

        return wrapper

    return decorator


def async_timeout(timeout_seconds: float):
    """Async timeout decorator."""

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_seconds,
                )
            except TimeoutError:
                logger.exception(
                    f"Function {func.__name__} timed out after {timeout_seconds}s",
                )
                raise

        return wrapper

    return decorator


def async_rate_limit(calls_per_second: float):
    """Async rate limiting decorator."""

    def decorator(func: Callable):
        last_called = 0.0
        min_interval = 1.0 / calls_per_second

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            nonlocal last_called

            current_time = time.time()
            time_since_last = current_time - last_called

            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                await asyncio.sleep(sleep_time)

            last_called = time.time()
            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Global task manager
task_manager = AsyncTaskManager()


async def process_concurrent_tasks(
    tasks: list[Awaitable[Any]],
    max_concurrent: int = 10,
) -> list[Any]:
    """Process multiple tasks with controlled concurrency."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _process_task(task):
        async with semaphore:
            return await task

    # Execute all tasks with concurrency control
    return await asyncio.gather(*[_process_task(task) for task in tasks])


async def batch_process_items(
    items: list[Any],
    processor: Callable[[Any], Awaitable[Any]],
    batch_size: int = 50,
    max_concurrent: int = 10,
) -> list[Any]:
    """Process items in batches with controlled concurrency."""
    results = []

    # Process items in batches
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]

        # Create tasks for batch
        tasks = [processor(item) for item in batch]

        # Process batch with concurrency control
        batch_results = await process_concurrent_tasks(tasks, max_concurrent)
        results.extend(batch_results)

    return results
