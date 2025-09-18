"""
Klerno Labs Enterprise Integration Hub
Master orchestration system for all enterprise components
"""
import asyncio
import logging
import threading
import time
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path
import signal
import sys

# Import all enterprise systems
from .enterprise_database_async import get_database_manager
from .enterprise_error_handling import get_error_handler
from .enterprise_cicd_pipeline import CICDPipeline
from .enterprise_health_dashboard import get_health_monitor
from .enterprise_analytics_reporting import get_analytics_system

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SystemStatus:
    """System component status"""
    component_name: str
    status: str  # running, stopped, error, starting
    last_check: datetime
    health_score: float = 100.0
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)

@dataclass
class IntegrationConfig:
    """Enterprise integration configuration"""
    enable_database_pooling: bool = True
    enable_error_handling: bool = True
    enable_cicd_pipeline: bool = True
    enable_health_monitoring: bool = True
    enable_analytics: bool = True
    
    # Performance settings
    max_concurrent_operations: int = 100
    health_check_interval: int = 30
    analytics_update_interval: int = 300
    
    # Alert settings
    enable_alerts: bool = True
    alert_on_health_degradation: bool = True
    alert_threshold_warning: float = 80.0
    alert_threshold_critical: float = 50.0

class EnterpriseIntegrationHub:
    """Master orchestration system for all enterprise components"""
    
    def __init__(self, config: IntegrationConfig = None):
        self.config = config or IntegrationConfig()
        self.system_status: Dict[str, SystemStatus] = {}
        self.is_running = False
        
        # Enterprise components
        self.database_manager = None
        self.error_handler = None
        self.cicd_pipeline = None
        self.health_monitor = None
        self.analytics_system = None
        
        # Background workers
        self._workers: List[threading.Thread] = []
        self._shutdown_event = threading.Event()
        
        # Performance tracking
        self.start_time = datetime.now()
        self.operation_counts = {}
        self.performance_metrics = {}
        
        logger.info("[ENTERPRISE] Integration Hub initialized")
    
    async def initialize_all_systems(self) -> bool:
        """Initialize all enterprise systems"""
        logger.info("[ENTERPRISE] Starting enterprise systems initialization...")
        
        success_count = 0
        total_systems = 5
        
        try:
            # Initialize database system
            if self.config.enable_database_pooling:
                logger.info("[ENTERPRISE] Initializing database system...")
                self.database_manager = get_database_manager()
                await self.database_manager.initialize()
                self._update_system_status("database", "running", {"pool_size": 20})
                success_count += 1
                logger.info("[ENTERPRISE] ✅ Database system initialized")
            
            # Initialize error handling
            if self.config.enable_error_handling:
                logger.info("[ENTERPRISE] Initializing error handling...")
                self.error_handler = get_error_handler()
                self._update_system_status("error_handling", "running", {"circuit_breaker_state": "CLOSED"})
                success_count += 1
                logger.info("[ENTERPRISE] ✅ Error handling initialized")
            
            # Initialize CI/CD pipeline
            if self.config.enable_cicd_pipeline:
                logger.info("[ENTERPRISE] Initializing CI/CD pipeline...")
                self.cicd_pipeline = CICDPipeline()
                self._update_system_status("cicd_pipeline", "running", {"pipeline_stages": 7})
                success_count += 1
                logger.info("[ENTERPRISE] ✅ CI/CD pipeline initialized")
            
            # Initialize health monitoring
            if self.config.enable_health_monitoring:
                logger.info("[ENTERPRISE] Initializing health monitoring...")
                self.health_monitor = get_health_monitor()
                self._update_system_status("health_monitoring", "running", {"checks_registered": 5})
                success_count += 1
                logger.info("[ENTERPRISE] ✅ Health monitoring initialized")
            
            # Initialize analytics
            if self.config.enable_analytics:
                logger.info("[ENTERPRISE] Initializing analytics system...")
                self.analytics_system = get_analytics_system()
                self._update_system_status("analytics", "running", {"metrics_registered": 4})
                success_count += 1
                logger.info("[ENTERPRISE] ✅ Analytics system initialized")
            
            # Start background workers
            self._start_background_workers()
            
            self.is_running = True
            
            logger.info(f"[ENTERPRISE] ✅ Enterprise initialization complete: {success_count}/{total_systems} systems online")
            
            # Track initialization event
            if self.analytics_system:
                self.analytics_system.track_event(
                    "enterprise_initialization",
                    properties={
                        "systems_online": success_count,
                        "total_systems": total_systems,
                        "success_rate": (success_count / total_systems) * 100
                    }
                )
            
            return success_count == total_systems
            
        except Exception as e:
            logger.error(f"[ENTERPRISE] Failed to initialize enterprise systems: {e}")
            
            if self.error_handler:
                self.error_handler.handle_error(e, "enterprise_initialization")
            
            return False
    
    def _update_system_status(self, component: str, status: str, metrics: Dict = None):
        """Update system component status"""
        self.system_status[component] = SystemStatus(
            component_name=component,
            status=status,
            last_check=datetime.now(),
            metrics=metrics or {}
        )
    
    def _start_background_workers(self):
        """Start background monitoring workers"""
        
        # Health monitoring worker
        health_worker = threading.Thread(
            target=self._health_monitoring_worker,
            daemon=True,
            name="HealthMonitorWorker"
        )
        health_worker.start()
        self._workers.append(health_worker)
        
        # Performance monitoring worker
        perf_worker = threading.Thread(
            target=self._performance_monitoring_worker,
            daemon=True,
            name="PerformanceMonitorWorker"
        )
        perf_worker.start()
        self._workers.append(perf_worker)
        
        # Integration health worker
        integration_worker = threading.Thread(
            target=self._integration_health_worker,
            daemon=True,
            name="IntegrationHealthWorker"
        )
        integration_worker.start()
        self._workers.append(integration_worker)
        
        logger.info(f"[ENTERPRISE] Started {len(self._workers)} background workers")
    
    def _health_monitoring_worker(self):
        """Background worker for health monitoring"""
        while not self._shutdown_event.is_set():
            try:
                if self.health_monitor:
                    # Get overall system health
                    health_data = self.health_monitor.get_dashboard_data()
                    overall_health = health_data.get('overall_status', {}).get('health_score', 100)
                    
                    # Update performance metrics
                    self.performance_metrics['system_health'] = overall_health
                    
                    # Check for alerts
                    if overall_health < self.config.alert_threshold_critical:
                        self._trigger_alert("CRITICAL", f"System health critical: {overall_health}%")
                    elif overall_health < self.config.alert_threshold_warning:
                        self._trigger_alert("WARNING", f"System health degraded: {overall_health}%")
                    
                    # Track analytics
                    if self.analytics_system:
                        self.analytics_system.track_event(
                            "health_check",
                            properties={
                                "overall_health": overall_health,
                                "timestamp": datetime.now().isoformat()
                            }
                        )
                
                time.sleep(self.config.health_check_interval)
                
            except Exception as e:
                logger.error(f"[ENTERPRISE] Health monitoring worker error: {e}")
                time.sleep(self.config.health_check_interval)
    
    def _performance_monitoring_worker(self):
        """Background worker for performance monitoring"""
        while not self._shutdown_event.is_set():
            try:
                # Collect performance metrics from all systems
                metrics = {}
                
                # Database metrics
                if self.database_manager:
                    db_stats = self.database_manager.get_performance_stats()
                    metrics['database'] = {
                        'active_connections': db_stats.get('active_connections', 0),
                        'pool_utilization': db_stats.get('pool_utilization', 0),
                        'avg_query_time': db_stats.get('avg_query_time', 0)
                    }
                
                # Error handler metrics
                if self.error_handler:
                    error_stats = self.error_handler.get_error_statistics()
                    metrics['error_handling'] = {
                        'total_errors': error_stats.get('total_errors', 0),
                        'error_rate': error_stats.get('error_rate', 0),
                        'circuit_breaker_state': error_stats.get('circuit_breaker_state', 'UNKNOWN')
                    }
                
                # Store metrics
                self.performance_metrics.update(metrics)
                
                # Track in analytics
                if self.analytics_system:
                    for system, system_metrics in metrics.items():
                        for metric_name, value in system_metrics.items():
                            if isinstance(value, (int, float)):
                                self.analytics_system.track_event(
                                    "performance_metric",
                                    properties={
                                        "system": system,
                                        "metric": metric_name,
                                        "value": value
                                    }
                                )
                
                time.sleep(self.config.analytics_update_interval)
                
            except Exception as e:
                logger.error(f"[ENTERPRISE] Performance monitoring worker error: {e}")
                time.sleep(self.config.analytics_update_interval)
    
    def _integration_health_worker(self):
        """Background worker for integration health checks"""
        while not self._shutdown_event.is_set():
            try:
                # Check each system's health
                for component in self.system_status.keys():
                    health_score = self._check_component_health(component)
                    
                    if component in self.system_status:
                        self.system_status[component].health_score = health_score
                        self.system_status[component].last_check = datetime.now()
                        
                        if health_score < 50:
                            self.system_status[component].status = "error"
                        elif health_score < 80:
                            self.system_status[component].status = "degraded"
                        else:
                            self.system_status[component].status = "running"
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"[ENTERPRISE] Integration health worker error: {e}")
                time.sleep(60)
    
    def _check_component_health(self, component: str) -> float:
        """Check health of a specific component"""
        try:
            if component == "database" and self.database_manager:
                # Check database connectivity and performance
                stats = self.database_manager.get_performance_stats()
                utilization = stats.get('pool_utilization', 0)
                if utilization > 90:
                    return 50.0  # Critical
                elif utilization > 70:
                    return 80.0  # Warning
                return 100.0
            
            elif component == "error_handling" and self.error_handler:
                # Check error rates
                stats = self.error_handler.get_error_statistics()
                error_rate = stats.get('error_rate', 0)
                if error_rate > 10:
                    return 30.0  # Critical
                elif error_rate > 5:
                    return 70.0  # Warning
                return 100.0
            
            elif component == "health_monitoring" and self.health_monitor:
                # Health monitor is self-reporting
                return 100.0
            
            elif component == "analytics" and self.analytics_system:
                # Analytics system health
                return 100.0
            
            elif component == "cicd_pipeline" and self.cicd_pipeline:
                # CI/CD pipeline health
                return 100.0
            
            return 100.0
            
        except Exception as e:
            logger.error(f"[ENTERPRISE] Failed to check {component} health: {e}")
            return 0.0
    
    def _trigger_alert(self, severity: str, message: str):
        """Trigger system alert"""
        if not self.config.enable_alerts:
            return
        
        alert_data = {
            'severity': severity,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'system': 'enterprise_integration'
        }
        
        logger.warning(f"[ENTERPRISE] ALERT [{severity}]: {message}")
        
        # Store alert in health monitoring
        if self.health_monitor:
            try:
                # Create alert rule and trigger
                rule_id = f"integration_alert_{int(time.time())}"
                self.health_monitor.create_alert_rule(
                    rule_id=rule_id,
                    condition="system_health < threshold",
                    threshold=self.config.alert_threshold_warning,
                    severity=severity.lower(),
                    actions=["log", "notify"]
                )
            except Exception as e:
                logger.error(f"[ENTERPRISE] Failed to store alert: {e}")
        
        # Track in analytics
        if self.analytics_system:
            self.analytics_system.track_event(
                "system_alert",
                properties=alert_data
            )
    
    def get_enterprise_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive enterprise dashboard"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        dashboard = {
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': uptime,
            'is_running': self.is_running,
            'config': {
                'database_pooling': self.config.enable_database_pooling,
                'error_handling': self.config.enable_error_handling,
                'cicd_pipeline': self.config.enable_cicd_pipeline,
                'health_monitoring': self.config.enable_health_monitoring,
                'analytics': self.config.enable_analytics
            },
            'system_status': {
                name: {
                    'status': status.status,
                    'health_score': status.health_score,
                    'last_check': status.last_check.isoformat(),
                    'metrics': status.metrics
                }
                for name, status in self.system_status.items()
            },
            'performance_metrics': self.performance_metrics,
            'operation_counts': self.operation_counts
        }
        
        # Add component-specific data
        if self.health_monitor:
            try:
                health_data = self.health_monitor.get_dashboard_data()
                dashboard['health_data'] = health_data
            except Exception as e:
                logger.error(f"[ENTERPRISE] Failed to get health data: {e}")
        
        if self.analytics_system:
            try:
                analytics_data = self.analytics_system.get_analytics_dashboard()
                dashboard['analytics_data'] = analytics_data
            except Exception as e:
                logger.error(f"[ENTERPRISE] Failed to get analytics data: {e}")
        
        return dashboard
    
    async def execute_enterprise_operation(self, operation_type: str, operation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute enterprise operation with full monitoring"""
        operation_id = f"{operation_type}_{int(time.time() * 1000)}"
        start_time = time.time()
        
        # Track operation start
        if self.analytics_system:
            self.analytics_system.track_event(
                "enterprise_operation_start",
                properties={
                    "operation_id": operation_id,
                    "operation_type": operation_type,
                    "start_time": datetime.now().isoformat()
                }
            )
        
        try:
            # Execute operation with error handling
            if self.error_handler:
                @self.error_handler.circuit_breaker(f"enterprise_operation_{operation_type}")
                async def execute_with_protection():
                    return await self._execute_operation_internal(operation_type, operation_data)
                
                result = await execute_with_protection()
            else:
                result = await self._execute_operation_internal(operation_type, operation_data)
            
            execution_time = time.time() - start_time
            
            # Track successful completion
            if self.analytics_system:
                self.analytics_system.track_event(
                    "enterprise_operation_complete",
                    properties={
                        "operation_id": operation_id,
                        "operation_type": operation_type,
                        "execution_time": execution_time,
                        "status": "success"
                    }
                )
            
            # Update operation counts
            self.operation_counts[operation_type] = self.operation_counts.get(operation_type, 0) + 1
            
            return {
                'operation_id': operation_id,
                'status': 'success',
                'execution_time': execution_time,
                'result': result
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Track failed operation
            if self.analytics_system:
                self.analytics_system.track_event(
                    "enterprise_operation_error",
                    properties={
                        "operation_id": operation_id,
                        "operation_type": operation_type,
                        "execution_time": execution_time,
                        "error": str(e)
                    }
                )
            
            # Handle error
            if self.error_handler:
                self.error_handler.handle_error(e, f"enterprise_operation_{operation_type}")
            
            logger.error(f"[ENTERPRISE] Operation {operation_id} failed: {e}")
            
            return {
                'operation_id': operation_id,
                'status': 'error',
                'execution_time': execution_time,
                'error': str(e)
            }
    
    async def _execute_operation_internal(self, operation_type: str, operation_data: Dict[str, Any]) -> Any:
        """Internal operation execution"""
        
        if operation_type == "database_query":
            if self.database_manager:
                return await self.database_manager.execute_query(
                    operation_data.get('query'),
                    operation_data.get('params', [])
                )
        
        elif operation_type == "run_cicd_pipeline":
            if self.cicd_pipeline:
                return self.cicd_pipeline.run_pipeline(
                    operation_data.get('project_path'),
                    operation_data.get('target_env', 'development')
                )
        
        elif operation_type == "generate_report":
            if self.analytics_system:
                return self.analytics_system.generate_report(
                    operation_data.get('report_id'),
                    operation_data.get('parameters', {})
                )
        
        elif operation_type == "health_check":
            if self.health_monitor:
                return self.health_monitor.get_dashboard_data()
        
        else:
            raise ValueError(f"Unknown operation type: {operation_type}")
    
    async def shutdown(self):
        """Shutdown all enterprise systems"""
        logger.info("[ENTERPRISE] Starting enterprise shutdown...")
        
        self.is_running = False
        self._shutdown_event.set()
        
        # Track shutdown event
        if self.analytics_system:
            self.analytics_system.track_event(
                "enterprise_shutdown",
                properties={
                    "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
                    "operation_counts": self.operation_counts
                }
            )
        
        # Shutdown components
        if self.database_manager:
            await self.database_manager.shutdown()
            logger.info("[ENTERPRISE] ✅ Database manager shutdown")
        
        if self.error_handler:
            # Error handler doesn't need explicit shutdown
            logger.info("[ENTERPRISE] ✅ Error handler stopped")
        
        if self.health_monitor:
            self.health_monitor.shutdown()
            logger.info("[ENTERPRISE] ✅ Health monitor shutdown")
        
        if self.analytics_system:
            self.analytics_system.shutdown()
            logger.info("[ENTERPRISE] ✅ Analytics system shutdown")
        
        # Wait for workers to finish
        for worker in self._workers:
            if worker.is_alive():
                worker.join(timeout=5)
        
        logger.info("[ENTERPRISE] Enterprise integration hub shutdown complete")

# Global enterprise hub instance
enterprise_hub = None

def get_enterprise_hub() -> EnterpriseIntegrationHub:
    """Get global enterprise hub instance"""
    global enterprise_hub
    
    if enterprise_hub is None:
        enterprise_hub = EnterpriseIntegrationHub()
    
    return enterprise_hub

async def initialize_enterprise():
    """Initialize complete enterprise system"""
    try:
        hub = get_enterprise_hub()
        success = await hub.initialize_all_systems()
        
        if success:
            logger.info("[ENTERPRISE] 🚀 Enterprise system fully operational!")
            return hub
        else:
            logger.error("[ENTERPRISE] ❌ Enterprise initialization failed")
            return None
            
    except Exception as e:
        logger.error(f"[ENTERPRISE] Enterprise initialization error: {e}")
        return None

def setup_signal_handlers(hub: EnterpriseIntegrationHub):
    """Setup graceful shutdown signal handlers"""
    def signal_handler(signum, frame):
        logger.info(f"[ENTERPRISE] Received signal {signum}, initiating shutdown...")
        asyncio.create_task(hub.shutdown())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    # Run enterprise system
    async def main():
        hub = await initialize_enterprise()
        
        if hub:
            setup_signal_handlers(hub)
            
            # Keep running
            try:
                while hub.is_running:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                await hub.shutdown()
    
    asyncio.run(main())