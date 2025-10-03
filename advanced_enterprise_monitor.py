#!/usr/bin/env python3
"""
KLERNO LABS ENTERPRISE PLATFORM - ADVANCED MONITORING SUITE V2
===============================================================

Real-time monitoring, metrics collection, and observability for enterprise deployment.
Enhanced version with comprehensive system and application monitoring.
"""

import asyncio
import json
import logging
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import psutil


@dataclass
class SystemMetrics:
    """System resource metrics"""

    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_usage_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    active_connections: int


@dataclass
class ApplicationMetrics:
    """Application-specific metrics"""

    timestamp: str
    active_requests: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time: float
    endpoint_stats: Dict[str, Any]
    cache_hit_rate: float
    database_connections: int


@dataclass
class APIHealthCheck:
    """API endpoint health check result"""

    endpoint: str
    status_code: int
    response_time: float
    success: bool
    error_message: Optional[str] = None


class AdvancedEnterpriseMonitor:
    """Advanced monitoring and observability system with live API testing"""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        log_file: str = "logs/enterprise_monitor_v2.log",
    ):
        self.base_url = base_url
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(exist_ok=True)

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(self.log_file), logging.StreamHandler()],
        )
        self.logger = logging.getLogger("AdvancedEnterpriseMonitor")

        self.system_metrics: List[SystemMetrics] = []
        self.app_metrics: List[ApplicationMetrics] = []
        self.api_health_checks: List[APIHealthCheck] = []
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None

        # Monitoring intervals
        self.system_interval = 10  # seconds
        self.app_interval = 15  # seconds
        self.api_interval = 20  # seconds

        # Alerting thresholds
        self.cpu_threshold = 80.0
        self.memory_threshold = 85.0
        self.response_time_threshold = 1.0

        # API endpoints to monitor
        self.monitored_endpoints = [
            "/health",
            "/status",
            "/enterprise/status",
            "/enterprise/health",
            "/docs",
            "/openapi.json",
        ]

    def collect_system_metrics(self) -> SystemMetrics:
        """Collect current system resource metrics"""
        try:
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()

            # Disk usage
            disk = psutil.disk_usage("/")

            # Network stats
            network = psutil.net_io_counters()

            # Active connections
            connections = len(psutil.net_connections())

            return SystemMetrics(
                timestamp=datetime.now().isoformat(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / 1024 / 1024,
                disk_usage_percent=(disk.used / disk.total) * 100,
                network_bytes_sent=network.bytes_sent,
                network_bytes_recv=network.bytes_recv,
                active_connections=connections,
            )
        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
            return None

    async def check_api_endpoint(
        self, session: aiohttp.ClientSession, endpoint: str
    ) -> APIHealthCheck:
        """Check health of a specific API endpoint"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()

        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                response_time = time.time() - start_time
                success = response.status == 200

                return APIHealthCheck(
                    endpoint=endpoint,
                    status_code=response.status,
                    response_time=response_time,
                    success=success,
                    error_message=None if success else f"HTTP {response.status}",
                )
        except Exception as e:
            response_time = time.time() - start_time
            return APIHealthCheck(
                endpoint=endpoint,
                status_code=0,
                response_time=response_time,
                success=False,
                error_message=str(e),
            )

    async def collect_api_metrics(self) -> List[APIHealthCheck]:
        """Collect API health metrics for all monitored endpoints"""
        health_checks = []

        try:
            async with aiohttp.ClientSession() as session:
                tasks = [
                    self.check_api_endpoint(session, endpoint)
                    for endpoint in self.monitored_endpoints
                ]
                health_checks = await asyncio.gather(*tasks, return_exceptions=True)

                # Filter out exceptions
                health_checks = [
                    hc for hc in health_checks if isinstance(hc, APIHealthCheck)
                ]

        except Exception as e:
            self.logger.error(f"Failed to collect API metrics: {e}")

        return health_checks

    def simulate_application_metrics(
        self, api_health_checks: List[APIHealthCheck]
    ) -> ApplicationMetrics:
        """Generate application metrics based on API health checks"""
        # Calculate success metrics from API health checks
        successful_apis = sum(1 for hc in api_health_checks if hc.success)
        total_apis = len(api_health_checks)
        avg_response_time = (
            sum(hc.response_time for hc in api_health_checks) / total_apis
            if total_apis > 0
            else 0
        )

        # Create endpoint stats
        endpoint_stats = {}
        for hc in api_health_checks:
            endpoint_stats[hc.endpoint] = {
                "status_code": hc.status_code,
                "response_time": hc.response_time,
                "success": hc.success,
                "error": hc.error_message,
            }

        return ApplicationMetrics(
            timestamp=datetime.now().isoformat(),
            active_requests=0,
            total_requests=total_apis * 100,  # Simulated
            successful_requests=successful_apis * 100,
            failed_requests=(total_apis - successful_apis) * 100,
            average_response_time=avg_response_time,
            endpoint_stats=endpoint_stats,
            cache_hit_rate=0.85,  # Simulated
            database_connections=5,  # Simulated
        )

    def check_alerts(
        self, system_metrics: SystemMetrics, app_metrics: ApplicationMetrics
    ):
        """Check for alert conditions and log warnings"""
        alerts = []

        # System alerts
        if system_metrics and system_metrics.cpu_percent > self.cpu_threshold:
            alerts.append(f"HIGH CPU: {system_metrics.cpu_percent:.1f}%")

        if system_metrics and system_metrics.memory_percent > self.memory_threshold:
            alerts.append(f"HIGH MEMORY: {system_metrics.memory_percent:.1f}%")

        # Application alerts
        if app_metrics.average_response_time > self.response_time_threshold:
            alerts.append(f"SLOW RESPONSE: {app_metrics.average_response_time:.3f}s")

        error_rate = (
            (app_metrics.failed_requests / app_metrics.total_requests) * 100
            if app_metrics.total_requests > 0
            else 0
        )
        if error_rate > 5.0:
            alerts.append(f"HIGH ERROR RATE: {error_rate:.1f}%")

        # API endpoint alerts
        failed_endpoints = [
            ep
            for ep, stats in app_metrics.endpoint_stats.items()
            if not stats["success"]
        ]
        if failed_endpoints:
            alerts.append(f"FAILED ENDPOINTS: {', '.join(failed_endpoints)}")

        # Log alerts
        for alert in alerts:
            self.logger.warning(f"ALERT: {alert}")

    def monitoring_loop(self):
        """Main monitoring loop with async API checks"""
        self.logger.info("Advanced enterprise monitoring started")
        last_system_check = 0
        last_app_check = 0
        last_api_check = 0

        while self.monitoring_active:
            current_time = time.time()

            # Collect system metrics
            if current_time - last_system_check >= self.system_interval:
                system_metrics = self.collect_system_metrics()
                if system_metrics:
                    self.system_metrics.append(system_metrics)
                    last_system_check = current_time

                    # Keep only last 100 readings
                    if len(self.system_metrics) > 100:
                        self.system_metrics = self.system_metrics[-100:]

            # Collect API and application metrics
            if current_time - last_api_check >= self.api_interval:
                try:
                    # Run async API checks
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    api_health_checks = loop.run_until_complete(
                        self.collect_api_metrics()
                    )
                    loop.close()

                    # Store API health checks
                    self.api_health_checks.extend(api_health_checks)
                    if len(self.api_health_checks) > 500:  # Keep last 500 checks
                        self.api_health_checks = self.api_health_checks[-500:]

                    # Generate application metrics
                    app_metrics = self.simulate_application_metrics(api_health_checks)
                    self.app_metrics.append(app_metrics)

                    # Keep only last 100 readings
                    if len(self.app_metrics) > 100:
                        self.app_metrics = self.app_metrics[-100:]

                    last_api_check = current_time
                    last_app_check = current_time

                    # Check for alerts
                    system_metrics = (
                        self.system_metrics[-1] if self.system_metrics else None
                    )
                    self.check_alerts(system_metrics, app_metrics)

                except Exception as e:
                    self.logger.error(f"Failed to collect API/application metrics: {e}")

            time.sleep(2)  # Check every 2 seconds

        self.logger.info("Advanced enterprise monitoring stopped")

    def start_monitoring(self):
        """Start the monitoring system"""
        if self.monitoring_active:
            self.logger.warning("Monitoring already active")
            return

        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self.monitoring_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Advanced monitoring thread started")

    def stop_monitoring(self):
        """Stop the monitoring system"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self.logger.info("Advanced monitoring stopped")

    def get_comprehensive_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report including API status"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_health": "HEALTHY",
            "system_health": {},
            "application_health": {},
            "api_health": {},
            "monitoring_stats": {},
        }

        # System health
        if self.system_metrics:
            latest_system = self.system_metrics[-1]
            recent_system = (
                self.system_metrics[-10:]
                if len(self.system_metrics) >= 10
                else self.system_metrics
            )

            avg_cpu = sum(m.cpu_percent for m in recent_system) / len(recent_system)
            avg_memory = sum(m.memory_percent for m in recent_system) / len(
                recent_system
            )

            system_status = "HEALTHY"
            if avg_cpu > self.cpu_threshold or avg_memory > self.memory_threshold:
                system_status = "WARNING"
                report["overall_health"] = "WARNING"
            if avg_cpu > 95 or avg_memory > 95:
                system_status = "CRITICAL"
                report["overall_health"] = "CRITICAL"

            report["system_health"] = {
                "status": system_status,
                "cpu_percent": latest_system.cpu_percent,
                "memory_percent": latest_system.memory_percent,
                "disk_usage_percent": latest_system.disk_usage_percent,
                "active_connections": latest_system.active_connections,
                "averages": {"cpu_percent": avg_cpu, "memory_percent": avg_memory},
            }

        # Application health
        if self.app_metrics:
            latest_app = self.app_metrics[-1]
            success_rate = (
                (latest_app.successful_requests / latest_app.total_requests) * 100
                if latest_app.total_requests > 0
                else 0
            )

            app_status = "HEALTHY"
            if (
                success_rate < 95
                or latest_app.average_response_time > self.response_time_threshold
            ):
                app_status = "WARNING"
                if report["overall_health"] != "CRITICAL":
                    report["overall_health"] = "WARNING"
            if success_rate < 90 or latest_app.average_response_time > 2.0:
                app_status = "CRITICAL"
                report["overall_health"] = "CRITICAL"

            report["application_health"] = {
                "status": app_status,
                "success_rate": success_rate,
                "average_response_time": latest_app.average_response_time,
                "total_requests": latest_app.total_requests,
                "failed_requests": latest_app.failed_requests,
                "cache_hit_rate": latest_app.cache_hit_rate,
                "database_connections": latest_app.database_connections,
            }

        # API health
        if self.api_health_checks:
            recent_api_checks = self.api_health_checks[
                -len(self.monitored_endpoints) :
            ]  # Last check for each endpoint
            successful_apis = sum(1 for hc in recent_api_checks if hc.success)
            total_apis = len(recent_api_checks)
            api_success_rate = (
                (successful_apis / total_apis) * 100 if total_apis > 0 else 0
            )

            api_status = "HEALTHY"
            if api_success_rate < 100:
                api_status = "WARNING"
                if report["overall_health"] != "CRITICAL":
                    report["overall_health"] = "WARNING"
            if api_success_rate < 80:
                api_status = "CRITICAL"
                report["overall_health"] = "CRITICAL"

            endpoint_details = {}
            for hc in recent_api_checks:
                endpoint_details[hc.endpoint] = {
                    "status_code": hc.status_code,
                    "response_time": hc.response_time,
                    "success": hc.success,
                    "error": hc.error_message,
                }

            report["api_health"] = {
                "status": api_status,
                "success_rate": api_success_rate,
                "total_endpoints": total_apis,
                "successful_endpoints": successful_apis,
                "endpoint_details": endpoint_details,
            }

        # Monitoring statistics
        report["monitoring_stats"] = {
            "system_metrics_collected": len(self.system_metrics),
            "app_metrics_collected": len(self.app_metrics),
            "api_checks_performed": len(self.api_health_checks),
            "monitoring_duration_minutes": (
                len(self.system_metrics) * self.system_interval
            )
            / 60,
        }

        return report

    def export_metrics(self, filename: str = "enterprise_metrics_v2.json"):
        """Export collected metrics to JSON file"""
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "system_metrics": [asdict(m) for m in self.system_metrics],
            "application_metrics": [asdict(m) for m in self.app_metrics],
            "api_health_checks": [asdict(hc) for hc in self.api_health_checks],
            "comprehensive_health_report": self.get_comprehensive_health_report(),
        }

        with open(filename, "w") as f:
            json.dump(export_data, f, indent=2)

        self.logger.info(f"Advanced metrics exported to {filename}")

    def generate_monitoring_report(self):
        """Generate comprehensive monitoring report"""
        print("\n🔍 KLERNO LABS ADVANCED ENTERPRISE MONITORING REPORT")
        print("=" * 70)

        health_report = self.get_comprehensive_health_report()

        # Overall health
        status_emoji = {"HEALTHY": "✅", "WARNING": "⚠️", "CRITICAL": "🚨"}
        overall_status = health_report["overall_health"]
        print(
            f"\n🎯 OVERALL HEALTH: {status_emoji.get(overall_status, '❓')} {overall_status}"
        )
        print("-" * 50)

        # System health
        if "system_health" in health_report:
            sys_health = health_report["system_health"]
            print(
                f"\n🖥️  SYSTEM HEALTH: {status_emoji.get(sys_health['status'], '❓')} {sys_health['status']}"
            )
            print("-" * 30)
            print(
                f"CPU Usage: {sys_health['cpu_percent']:.1f}% (avg: {sys_health['averages']['cpu_percent']:.1f}%)"
            )
            print(
                f"Memory Usage: {sys_health['memory_percent']:.1f}% (avg: {sys_health['averages']['memory_percent']:.1f}%)"
            )
            print(f"Disk Usage: {sys_health['disk_usage_percent']:.1f}%")
            print(f"Active Connections: {sys_health['active_connections']}")

        # Application health
        if "application_health" in health_report:
            app_health = health_report["application_health"]
            print(
                f"\n🚀 APPLICATION HEALTH: {status_emoji.get(app_health['status'], '❓')} {app_health['status']}"
            )
            print("-" * 30)
            print(f"Success Rate: {app_health['success_rate']:.1f}%")
            print(f"Avg Response Time: {app_health['average_response_time']:.3f}s")
            print(f"Total Requests: {app_health['total_requests']}")
            print(f"Failed Requests: {app_health['failed_requests']}")
            print(f"Cache Hit Rate: {app_health['cache_hit_rate']:.1f}%")
            print(f"DB Connections: {app_health['database_connections']}")

        # API health
        if "api_health" in health_report:
            api_health = health_report["api_health"]
            print(
                f"\n🌐 API HEALTH: {status_emoji.get(api_health['status'], '❓')} {api_health['status']}"
            )
            print("-" * 30)
            print(f"API Success Rate: {api_health['success_rate']:.1f}%")
            print(f"Endpoints Monitored: {api_health['total_endpoints']}")
            print(f"Successful Endpoints: {api_health['successful_endpoints']}")

            print(f"\n📊 ENDPOINT DETAILS:")
            for endpoint, details in api_health["endpoint_details"].items():
                status_icon = "✅" if details["success"] else "❌"
                print(
                    f"  {status_icon} {endpoint}: {details['status_code']} ({details['response_time']:.3f}s)"
                )
                if details["error"]:
                    print(f"    Error: {details['error']}")

        # Monitoring statistics
        if "monitoring_stats" in health_report:
            stats = health_report["monitoring_stats"]
            print(f"\n📈 MONITORING STATISTICS")
            print("-" * 30)
            print(f"System Metrics: {stats['system_metrics_collected']}")
            print(f"App Metrics: {stats['app_metrics_collected']}")
            print(f"API Checks: {stats['api_checks_performed']}")
            print(f"Duration: {stats['monitoring_duration_minutes']:.1f} minutes")


def main():
    """Demonstrate advanced enterprise monitoring capabilities"""
    print("🔍 KLERNO LABS ADVANCED ENTERPRISE MONITORING SUITE")
    print("=" * 60)

    monitor = AdvancedEnterpriseMonitor()

    try:
        # Start monitoring
        monitor.start_monitoring()
        print(
            "✅ Advanced monitoring started. Collecting comprehensive metrics for 45 seconds..."
        )
        print("   - System resource monitoring every 10 seconds")
        print("   - API health checks every 20 seconds")
        print("   - Application metrics derived from API status")

        # Run for 45 seconds
        time.sleep(45)

        # Generate comprehensive report
        monitor.generate_monitoring_report()

        # Export detailed metrics
        monitor.export_metrics()

    except KeyboardInterrupt:
        print("\n⏹️  Monitoring interrupted by user")
    finally:
        monitor.stop_monitoring()
        print("✅ Advanced monitoring stopped")


if __name__ == "__main__":
    main()
