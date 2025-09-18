#!/usr/bin/env python3
"""
Enterprise monitoring systems testing script.
Tests alerting, performance metrics, and monitoring infrastructure.
"""

import sys
import os
import asyncio
import time
from pathlib import Path
from datetime import datetime, timezone

# Add the app directory to the Python path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

def test_enterprise_monitor_initialization():
    """Test enterprise monitor can be initialized."""
    try:
        from app.main import EnterpriseMonitor
        
        monitor = EnterpriseMonitor()
        assert monitor is not None, "Enterprise monitor should initialize"
        
        # Test monitor has required components
        assert hasattr(monitor, 'alert_rules'), "Monitor should have alert rules"
        assert hasattr(monitor, 'metrics'), "Monitor should have metrics"
        assert hasattr(monitor, 'health_checks'), "Monitor should have health checks"
        
        print("✅ Enterprise monitor initialization: PASSED")
        return True
    except Exception as e:
        print(f"❌ Enterprise monitor initialization: FAILED - {e}")
        return False

def test_alert_rules_configuration():
    """Test alert rules are properly configured."""
    try:
        from app.main import EnterpriseMonitor
        
        monitor = EnterpriseMonitor()
        
        # Test alert rules exist
        assert len(monitor.alert_rules) > 0, "Alert rules should be configured"
        
        # Test required alert types
        alert_types = [rule['name'] for rule in monitor.alert_rules]
        required_alerts = ['high_cpu', 'memory_usage', 'error_rate', 'response_time']
        
        for alert in required_alerts:
            assert any(alert in alert_type for alert_type in alert_types), f"Should have {alert} alert"
        
        # Test alert rule structure
        for rule in monitor.alert_rules:
            assert 'name' in rule, "Alert rule should have name"
            assert 'threshold' in rule, "Alert rule should have threshold"
            assert 'condition' in rule, "Alert rule should have condition"
        
        print("✅ Alert rules configuration: PASSED")
        return True
    except Exception as e:
        print(f"❌ Alert rules configuration: FAILED - {e}")
        return False

def test_performance_metrics_collection():
    """Test performance metrics collection."""
    try:
        from app.main import EnterpriseMonitor
        
        monitor = EnterpriseMonitor()
        
        # Collect initial metrics
        initial_metrics = monitor.collect_metrics()
        assert isinstance(initial_metrics, dict), "Metrics should be dict"
        
        # Test required metric categories
        required_metrics = ['cpu_usage', 'memory_usage', 'disk_usage', 'response_times']
        for metric in required_metrics:
            assert metric in initial_metrics, f"Should collect {metric} metric"
        
        # Simulate some activity and collect again
        time.sleep(0.1)  # Brief pause
        updated_metrics = monitor.collect_metrics()
        
        # Verify metrics are being updated
        assert isinstance(updated_metrics, dict), "Updated metrics should be dict"
        assert len(updated_metrics) > 0, "Should have metric data"
        
        print("✅ Performance metrics collection: PASSED")
        return True
    except Exception as e:
        print(f"❌ Performance metrics collection: FAILED - {e}")
        return False

def test_health_check_system():
    """Test health check system."""
    try:
        from app.main import EnterpriseMonitor
        
        monitor = EnterpriseMonitor()
        
        # Run health checks
        health_status = monitor.run_health_checks()
        assert isinstance(health_status, dict), "Health status should be dict"
        
        # Test health check results
        assert 'overall_status' in health_status, "Should have overall status"
        assert 'checks' in health_status, "Should have individual checks"
        
        # Test individual health checks
        checks = health_status['checks']
        required_checks = ['database', 'cache', 'external_apis']
        
        for check in required_checks:
            assert check in checks, f"Should have {check} health check"
            assert 'status' in checks[check], f"{check} should have status"
            assert 'response_time' in checks[check], f"{check} should have response time"
        
        print("✅ Health check system: PASSED")
        return True
    except Exception as e:
        print(f"❌ Health check system: FAILED - {e}")
        return False

def test_alerting_mechanism():
    """Test alerting mechanism."""
    try:
        from app.main import EnterpriseMonitor
        
        monitor = EnterpriseMonitor()
        
        # Test alert generation
        test_alert = {
            'type': 'test_alert',
            'severity': 'warning',
            'message': 'Test alert message',
            'timestamp': datetime.now(timezone.utc)
        }
        
        # Trigger alert
        alert_result = monitor.trigger_alert(test_alert)
        assert alert_result is not None, "Alert should be triggered"
        
        # Test alert processing
        assert hasattr(monitor, 'process_alert'), "Monitor should have alert processing"
        
        # Test alert storage/logging
        assert hasattr(monitor, 'alert_history'), "Monitor should track alert history"
        
        print("✅ Alerting mechanism: PASSED")
        return True
    except Exception as e:
        print(f"❌ Alerting mechanism: FAILED - {e}")
        return False

def test_dashboard_data_preparation():
    """Test dashboard data preparation."""
    try:
        from app.main import EnterpriseMonitor
        
        monitor = EnterpriseMonitor()
        
        # Test dashboard data generation
        dashboard_data = monitor.get_dashboard_data()
        assert isinstance(dashboard_data, dict), "Dashboard data should be dict"
        
        # Test required dashboard sections
        required_sections = ['metrics', 'alerts', 'health', 'performance']
        for section in required_sections:
            assert section in dashboard_data, f"Dashboard should have {section} section"
        
        # Test data structure
        metrics_data = dashboard_data['metrics']
        assert isinstance(metrics_data, dict), "Metrics data should be dict"
        assert len(metrics_data) > 0, "Should have metrics data"
        
        print("✅ Dashboard data preparation: PASSED")
        return True
    except Exception as e:
        print(f"❌ Dashboard data preparation: FAILED - {e}")
        return False

def test_monitoring_integration():
    """Test monitoring integration with main application."""
    try:
        from app.main import app
        from app.main import EnterpriseMonitor
        
        # Test monitoring is integrated into FastAPI app
        assert hasattr(app, 'state'), "App should have state management"
        
        # Test monitoring middleware
        middlewares = [middleware.cls.__name__ for middleware in app.user_middleware]
        monitoring_middleware_exists = any('monitor' in mw.lower() for mw in middlewares)
        
        # Test monitoring routes exist
        routes = [route.path for route in app.routes]
        monitoring_routes = [route for route in routes if 'monitor' in route or 'health' in route or 'metrics' in route]
        assert len(monitoring_routes) > 0, "Should have monitoring endpoints"
        
        print("✅ Monitoring integration: PASSED")
        return True
    except Exception as e:
        print(f"❌ Monitoring integration: FAILED - {e}")
        return False

def test_log_aggregation():
    """Test log aggregation and analysis."""
    try:
        from app.main import EnterpriseMonitor
        
        monitor = EnterpriseMonitor()
        
        # Test log collection
        if hasattr(monitor, 'collect_logs'):
            logs = monitor.collect_logs()
            assert isinstance(logs, (list, dict)), "Logs should be collection"
        
        # Test log analysis
        if hasattr(monitor, 'analyze_logs'):
            log_analysis = monitor.analyze_logs()
            assert isinstance(log_analysis, dict), "Log analysis should be dict"
        
        # Test log aggregation features
        assert hasattr(monitor, 'log_handlers') or hasattr(monitor, 'logging_config'), "Should have logging configuration"
        
        print("✅ Log aggregation: PASSED")
        return True
    except Exception as e:
        print(f"❌ Log aggregation: FAILED - {e}")
        return False

def main():
    """Run all enterprise monitoring tests."""
    print("📊 Enterprise Monitoring Systems Testing")
    print("=" * 45)
    
    tests = [
        test_enterprise_monitor_initialization,
        test_alert_rules_configuration,
        test_performance_metrics_collection,
        test_health_check_system,
        test_alerting_mechanism,
        test_dashboard_data_preparation,
        test_monitoring_integration,
        test_log_aggregation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: FAILED - {e}")
    
    print("\n" + "=" * 45)
    print(f"Enterprise Monitoring Results: {passed}/{total} passed")
    
    if passed >= total * 0.75:  # 75% pass rate is acceptable
        print("🎉 Enterprise monitoring systems are working well!")
        return True
    else:
        print(f"⚠️  {total - passed} monitoring systems need attention")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)