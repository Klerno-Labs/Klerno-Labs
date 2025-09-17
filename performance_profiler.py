#!/usr/bin/env python3
"""
Performance profiler for identifying bottlenecks in the Klerno Labs application.

This module provides comprehensive performance analysis tools to identify
hot paths, slow database queries, and optimization opportunities.
"""

import asyncio
import cProfile
import io
import logging
import pstats
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple

import psutil
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EndpointMetrics:
    """Metrics for a specific endpoint."""
    path: str
    method: str
    total_requests: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    error_count: int = 0
    avg_response_size: float = 0.0
    total_response_size: int = 0

    @property
    def avg_time(self) -> float:
        return self.total_time / max(self.total_requests, 1)

    @property
    def error_rate(self) -> float:
        return self.error_count / max(self.total_requests, 1)


@dataclass
class DatabaseQueryMetrics:
    """Metrics for database query patterns."""
    query_hash: str
    sample_query: str
    execution_count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    avg_rows_returned: float = 0.0
    total_rows: int = 0

    @property
    def avg_time(self) -> float:
        return self.total_time / max(self.execution_count, 1)


@dataclass
class SystemMetrics:
    """System-level performance metrics."""
    timestamp: datetime
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_bytes_sent: float
    network_bytes_recv: float


class PerformanceProfiler:
    """Main performance profiler for bottleneck analysis."""

    def __init__(self):
        self.endpoint_metrics: Dict[str, EndpointMetrics] = {}
        self.query_metrics: Dict[str, DatabaseQueryMetrics] = {}
        self.system_metrics: List[SystemMetrics] = []
        self.profiling_enabled = False
        self.profile_data: Optional[cProfile.Profile] = None

    def start_profiling(self) -> None:
        """Start performance profiling session."""
        self.profiling_enabled = True
        self.profile_data = cProfile.Profile()
        self.profile_data.enable()
        logger.info("Performance profiling started")

    def stop_profiling(self) -> str:
        """Stop profiling and return results."""
        if not self.profiling_enabled or not self.profile_data:
            return "Profiling not active"

        self.profile_data.disable()
        self.profiling_enabled = False

        # Generate profile report
        s = io.StringIO()
        ps = pstats.Stats(self.profile_data, stream=s)
        ps.sort_stats('cumulative')
        ps.print_stats(50)  # Top 50 functions

        logger.info("Performance profiling stopped")
        return s.getvalue()

    def profile_function(self, func: Callable) -> Callable:
        """Decorator to profile individual functions."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Log slow functions (>100ms)
                if execution_time > 0.1:
                    logger.warning(
                        f"Slow function detected: {func.__name__} took {execution_time:.3f}s"
                    )
                
                return result
            except Exception as e:
                logger.error(f"Function {func.__name__} failed: {e}")
                raise
        
        return wrapper

    async def profile_endpoint(self, url: str, method: str = "GET", **kwargs) -> Dict[str, Any]:
        """Profile a specific endpoint with multiple requests."""
        logger.info(f"Profiling endpoint: {method} {url}")
        
        metrics = {
            "url": url,
            "method": method,
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "response_times": [],
            "response_sizes": [],
            "errors": []
        }

        # Run multiple requests to get statistical data
        for i in range(10):
            try:
                start_time = time.time()
                
                if method.upper() == "GET":
                    response = requests.get(url, timeout=30, **kwargs)
                elif method.upper() == "POST":
                    response = requests.post(url, timeout=30, **kwargs)
                else:
                    continue

                end_time = time.time()
                response_time = end_time - start_time

                metrics["total_requests"] += 1
                metrics["response_times"].append(response_time)
                
                if response.status_code < 400:
                    metrics["successful_requests"] += 1
                    content_length = len(response.content)
                    metrics["response_sizes"].append(content_length)
                else:
                    metrics["failed_requests"] += 1
                    metrics["errors"].append(f"HTTP {response.status_code}")

                # Small delay between requests
                await asyncio.sleep(0.1)

            except Exception as e:
                metrics["total_requests"] += 1
                metrics["failed_requests"] += 1
                metrics["errors"].append(str(e))
                logger.error(f"Request failed: {e}")

        # Calculate statistics
        if metrics["response_times"]:
            metrics["avg_response_time"] = sum(metrics["response_times"]) / len(metrics["response_times"])
            metrics["min_response_time"] = min(metrics["response_times"])
            metrics["max_response_time"] = max(metrics["response_times"])
            metrics["p95_response_time"] = sorted(metrics["response_times"])[int(len(metrics["response_times"]) * 0.95)]

        if metrics["response_sizes"]:
            metrics["avg_response_size"] = sum(metrics["response_sizes"]) / len(metrics["response_sizes"])

        return metrics

    def collect_system_metrics(self) -> SystemMetrics:
        """Collect current system performance metrics."""
        # Get CPU and memory info
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        # Get disk I/O
        disk_io = psutil.disk_io_counters()
        disk_read_mb = disk_io.read_bytes / (1024 * 1024) if disk_io else 0
        disk_write_mb = disk_io.write_bytes / (1024 * 1024) if disk_io else 0
        
        # Get network I/O
        net_io = psutil.net_io_counters()
        net_sent = net_io.bytes_sent if net_io else 0
        net_recv = net_io.bytes_recv if net_io else 0

        metrics = SystemMetrics(
            timestamp=datetime.now(timezone.utc),
            cpu_percent=cpu_percent,
            memory_mb=memory.used / (1024 * 1024),
            memory_percent=memory.percent,
            disk_io_read_mb=disk_read_mb,
            disk_io_write_mb=disk_write_mb,
            network_bytes_sent=net_sent,
            network_bytes_recv=net_recv
        )

        self.system_metrics.append(metrics)
        
        # Keep only last 1000 metrics
        if len(self.system_metrics) > 1000:
            self.system_metrics = self.system_metrics[-1000:]

        return metrics

    async def analyze_bottlenecks(self, base_url: str = "http://localhost:8000") -> Dict[str, Any]:
        """Comprehensive bottleneck analysis."""
        logger.info("Starting comprehensive bottleneck analysis")
        
        # Critical endpoints to analyze
        endpoints_to_test = [
            {"path": "/health", "method": "GET"},
            {"path": "/status", "method": "GET"},
            {"path": "/enterprise/status", "method": "GET"},
            {"path": "/enterprise/performance/metrics", "method": "GET"},
            {"path": "/enterprise/iso20022/status", "method": "GET"},
            {"path": "/enterprise/quality-metrics", "method": "GET"},
        ]

        analysis_results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "endpoint_analysis": {},
            "system_baseline": {},
            "bottleneck_summary": {},
            "recommendations": []
        }

        # Collect baseline system metrics
        baseline_metrics = self.collect_system_metrics()
        analysis_results["system_baseline"] = {
            "cpu_percent": baseline_metrics.cpu_percent,
            "memory_mb": baseline_metrics.memory_mb,
            "memory_percent": baseline_metrics.memory_percent
        }

        # Test each endpoint
        for endpoint in endpoints_to_test:
            url = f"{base_url}{endpoint['path']}"
            try:
                metrics = await self.profile_endpoint(url, endpoint["method"])
                analysis_results["endpoint_analysis"][endpoint["path"]] = metrics
                
                # Identify slow endpoints
                if metrics.get("avg_response_time", 0) > 0.2:  # >200ms
                    analysis_results["recommendations"].append(
                        f"Endpoint {endpoint['path']} is slow (avg: {metrics.get('avg_response_time', 0):.3f}s)"
                    )
                    
            except Exception as e:
                logger.error(f"Failed to profile {url}: {e}")
                analysis_results["endpoint_analysis"][endpoint["path"]] = {"error": str(e)}

        # Generate bottleneck summary
        slow_endpoints = []
        for path, metrics in analysis_results["endpoint_analysis"].items():
            if isinstance(metrics, dict) and metrics.get("avg_response_time", 0) > 0.2:
                slow_endpoints.append({
                    "path": path,
                    "avg_time": metrics["avg_response_time"],
                    "max_time": metrics.get("max_response_time", 0)
                })

        analysis_results["bottleneck_summary"] = {
            "slow_endpoints_count": len(slow_endpoints),
            "slow_endpoints": slow_endpoints,
            "high_cpu_usage": baseline_metrics.cpu_percent > 70,
            "high_memory_usage": baseline_metrics.memory_percent > 80
        }

        # Add specific recommendations
        if baseline_metrics.cpu_percent > 70:
            analysis_results["recommendations"].append(
                f"High CPU usage detected: {baseline_metrics.cpu_percent:.1f}%"
            )

        if baseline_metrics.memory_percent > 80:
            analysis_results["recommendations"].append(
                f"High memory usage detected: {baseline_metrics.memory_percent:.1f}%"
            )

        if len(slow_endpoints) > 0:
            analysis_results["recommendations"].append(
                f"{len(slow_endpoints)} endpoints are performing slowly and need optimization"
            )

        logger.info("Bottleneck analysis completed")
        return analysis_results

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "endpoint_metrics": {
                path: {
                    "total_requests": metrics.total_requests,
                    "avg_time": metrics.avg_time,
                    "error_rate": metrics.error_rate
                }
                for path, metrics in self.endpoint_metrics.items()
            },
            "system_metrics_summary": {
                "total_samples": len(self.system_metrics),
                "avg_cpu_percent": sum(m.cpu_percent for m in self.system_metrics) / max(len(self.system_metrics), 1),
                "avg_memory_mb": sum(m.memory_mb for m in self.system_metrics) / max(len(self.system_metrics), 1)
            } if self.system_metrics else {},
            "profiling_active": self.profiling_enabled
        }


# Global profiler instance
profiler = PerformanceProfiler()


def profile_function(func: Callable) -> Callable:
    """Convenience decorator for function profiling."""
    return profiler.profile_function(func)


async def run_performance_analysis(base_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """Run comprehensive performance analysis."""
    return await profiler.analyze_bottlenecks(base_url)


if __name__ == "__main__":
    async def main():
        print("Starting performance analysis...")
        results = await run_performance_analysis()
        
        print("\n=== PERFORMANCE ANALYSIS RESULTS ===")
        print(f"Analysis completed at: {results['timestamp']}")
        
        print(f"\nSystem Baseline:")
        baseline = results['system_baseline']
        print(f"  CPU: {baseline.get('cpu_percent', 0):.1f}%")
        print(f"  Memory: {baseline.get('memory_mb', 0):.1f} MB ({baseline.get('memory_percent', 0):.1f}%)")
        
        print(f"\nBottleneck Summary:")
        summary = results['bottleneck_summary']
        print(f"  Slow endpoints: {summary['slow_endpoints_count']}")
        print(f"  High CPU usage: {summary['high_cpu_usage']}")
        print(f"  High memory usage: {summary['high_memory_usage']}")
        
        if summary['slow_endpoints']:
            print(f"\nSlow Endpoints:")
            for endpoint in summary['slow_endpoints']:
                print(f"  {endpoint['path']}: avg={endpoint['avg_time']:.3f}s, max={endpoint['max_time']:.3f}s")
        
        if results['recommendations']:
            print(f"\nRecommendations:")
            for rec in results['recommendations']:
                print(f"  • {rec}")
    
    asyncio.run(main())