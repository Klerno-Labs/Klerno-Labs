#!/usr/bin/env python3
"""
Performance optimization verification script for Klerno Labs application.
Verifies that all performance optimization features are working correctly.
"""
import asyncio
import aiohttp
import time
from typing import Dict, List
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

class PerformanceVerifier:
    """Verifies performance optimization systems."""
    
    def __init__(self):
        self.results: List[Dict] = []
        
    def log_verification(self, system: str, status: str, details: str = ""):
        """Log verification result."""
        result = {
            'system': system,
            'status': status,
            'details': details,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        self.results.append(result)
        
        status_emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_emoji} {system}: {status}")
        if details:
            print(f"   {details}")
    
    def verify_import_systems(self):
        """Verify that performance optimization systems can be imported."""
        print("\n🔧 VERIFYING PERFORMANCE OPTIMIZATION IMPORTS")
        print("=" * 60)
        
        try:
            from app.performance_optimization import PerformanceOptimizer
            self.log_verification("PerformanceOptimizer Import", "PASS", "Successfully imported")
        except Exception as e:
            self.log_verification("PerformanceOptimizer Import", "FAIL", f"Import error: {e}")
            
        try:
            from app.enterprise_monitoring import EnterpriseMonitoring
            self.log_verification("EnterpriseMonitoring Import", "PASS", "Successfully imported")
        except Exception as e:
            self.log_verification("EnterpriseMonitoring Import", "FAIL", f"Import error: {e}")
            
        try:
            from app.advanced_security import AdvancedSecurityOrchestrator
            self.log_verification("AdvancedSecurity Import", "PASS", "Successfully imported")
        except Exception as e:
            self.log_verification("AdvancedSecurity Import", "FAIL", f"Import error: {e}")
            
        try:
            from app.resilience_system import ResilienceSystem
            self.log_verification("ResilienceSystem Import", "PASS", "Successfully imported")
        except Exception as e:
            self.log_verification("ResilienceSystem Import", "FAIL", f"Import error: {e}")
    
    def verify_performance_optimizer_methods(self):
        """Verify PerformanceOptimizer has all required methods."""
        print("\n⚡ VERIFYING PERFORMANCE OPTIMIZER METHODS")
        print("=" * 60)
        
        try:
            from app.performance_optimization import PerformanceOptimizer
            optimizer = PerformanceOptimizer()
            
            # Check for critical async methods that were added
            methods_to_check = [
                'optimize_database_connections',
                'setup_load_balancer', 
                'get_performance_baseline',
                'initialize_cache_layers',
                'setup_health_monitoring'
            ]
            
            for method_name in methods_to_check:
                if hasattr(optimizer, method_name):
                    method = getattr(optimizer, method_name)
                    if asyncio.iscoroutinefunction(method):
                        self.log_verification(f"Method: {method_name}", "PASS", "Async method exists")
                    else:
                        self.log_verification(f"Method: {method_name}", "WARN", "Method exists but not async")
                else:
                    self.log_verification(f"Method: {method_name}", "FAIL", "Method missing")
                    
        except Exception as e:
            self.log_verification("PerformanceOptimizer Methods", "FAIL", f"Error checking methods: {e}")
    
    def verify_caching_systems(self):
        """Verify caching system configuration."""
        print("\n💾 VERIFYING CACHING SYSTEMS")
        print("=" * 60)
        
        try:
            from app.performance_optimization import PerformanceOptimizer
            optimizer = PerformanceOptimizer()
            
            # Test memory cache
            if hasattr(optimizer, 'memory_cache'):
                self.log_verification("Memory Cache", "PASS", "Memory cache initialized")
            else:
                self.log_verification("Memory Cache", "FAIL", "Memory cache not found")
            
            # Test Redis cache availability (expected to fail in test environment)
            try:
                import redis
                self.log_verification("Redis Module", "PASS", "Redis module available")
            except ImportError:
                self.log_verification("Redis Module", "FAIL", "Redis module not installed")
            
            # Test Memcached availability
            try:
                from pymemcache.client.base import Client
                self.log_verification("Memcached Module", "PASS", "Memcached module available")
            except ImportError:
                self.log_verification("Memcached Module", "FAIL", "Memcached module not installed")
                
        except Exception as e:
            self.log_verification("Caching Systems", "FAIL", f"Error checking caching: {e}")
    
    def verify_monitoring_systems(self):
        """Verify monitoring system configuration."""
        print("\n📊 VERIFYING MONITORING SYSTEMS")
        print("=" * 60)
        
        try:
            from app.enterprise_monitoring import EnterpriseMonitoring
            monitoring = EnterpriseMonitoring()
            
            # Check if monitoring has alert rules
            if hasattr(monitoring, 'alert_rules') and len(monitoring.alert_rules) > 0:
                self.log_verification("Alert Rules", "PASS", f"Found {len(monitoring.alert_rules)} alert rules")
            else:
                self.log_verification("Alert Rules", "FAIL", "No alert rules configured")
            
            # Check if monitoring has health checks
            if hasattr(monitoring, 'health_checks') and len(monitoring.health_checks) > 0:
                self.log_verification("Health Checks", "PASS", f"Found {len(monitoring.health_checks)} health checks")
            else:
                self.log_verification("Health Checks", "FAIL", "No health checks configured")
                
        except Exception as e:
            self.log_verification("Monitoring Systems", "FAIL", f"Error checking monitoring: {e}")
    
    def verify_security_systems(self):
        """Verify security system configuration.""" 
        print("\n🔒 VERIFYING SECURITY SYSTEMS")
        print("=" * 60)
        
        try:
            from app.advanced_security import AdvancedSecurityOrchestrator
            security = AdvancedSecurityOrchestrator()
            
            # Check behavioral analyzer
            if hasattr(security, 'behavioral_analyzer'):
                self.log_verification("Behavioral Analyzer", "PASS", "Behavioral analyzer initialized")
            else:
                self.log_verification("Behavioral Analyzer", "FAIL", "Behavioral analyzer missing")
            
            # Check threat intelligence
            if hasattr(security, 'threat_intelligence'):
                self.log_verification("Threat Intelligence", "PASS", "Threat intelligence initialized")
            else:
                self.log_verification("Threat Intelligence", "FAIL", "Threat intelligence missing")
                
        except Exception as e:
            self.log_verification("Security Systems", "FAIL", f"Error checking security: {e}")
    
    def verify_resilience_systems(self):
        """Verify resilience system configuration."""
        print("\n🛡️ VERIFYING RESILIENCE SYSTEMS")
        print("=" * 60)
        
        try:
            from app.resilience_system import ResilienceSystem
            resilience = ResilienceSystem()
            
            # Check circuit breakers
            if hasattr(resilience, 'circuit_breakers') and len(resilience.circuit_breakers) > 0:
                self.log_verification("Circuit Breakers", "PASS", f"Found {len(resilience.circuit_breakers)} circuit breakers")
            else:
                self.log_verification("Circuit Breakers", "FAIL", "No circuit breakers configured")
            
            # Check auto-healing
            if hasattr(resilience, 'auto_healing_enabled'):
                status = "enabled" if resilience.auto_healing_enabled else "disabled"
                self.log_verification("Auto-healing", "PASS", f"Auto-healing is {status}")
            else:
                self.log_verification("Auto-healing", "WARN", "Auto-healing status unknown")
                
        except Exception as e:
            self.log_verification("Resilience Systems", "FAIL", f"Error checking resilience: {e}")
    
    def verify_database_systems(self):
        """Verify database system configuration."""
        print("\n🗃️ VERIFYING DATABASE SYSTEMS")
        print("=" * 60)
        
        try:
            from app.core.database import get_database
            self.log_verification("Database Module", "PASS", "Database module imports successfully")
            
            # Check if models can be imported
            from app.models import User, AdminConfig
            self.log_verification("Database Models", "PASS", "Core models import successfully")
            
        except Exception as e:
            self.log_verification("Database Systems", "FAIL", f"Error checking database: {e}")
    
    def verify_enterprise_integration(self):
        """Verify enterprise integration system."""
        print("\n🏢 VERIFYING ENTERPRISE INTEGRATION")
        print("=" * 60)
        
        try:
            from app.enterprise_integration import EnterpriseIntegration
            enterprise = EnterpriseIntegration()
            
            self.log_verification("Enterprise Integration", "PASS", "Enterprise integration module imports successfully")
            
            # Check ISO20022 compliance
            try:
                from app.iso20022_compliance import ISO20022Compliance
                self.log_verification("ISO20022 Compliance", "PASS", "ISO20022 compliance module available")
            except Exception as e:
                self.log_verification("ISO20022 Compliance", "FAIL", f"ISO20022 error: {e}")
                
        except Exception as e:
            self.log_verification("Enterprise Integration", "FAIL", f"Error checking enterprise: {e}")
    
    def run_all_verifications(self):
        """Run all verification tests."""
        print("🚀 STARTING PERFORMANCE OPTIMIZATION VERIFICATION")
        print("=" * 70)
        print(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        verification_suites = [
            self.verify_import_systems,
            self.verify_performance_optimizer_methods,
            self.verify_caching_systems,
            self.verify_monitoring_systems,
            self.verify_security_systems,
            self.verify_resilience_systems,
            self.verify_database_systems,
            self.verify_enterprise_integration,
        ]
        
        for verification_suite in verification_suites:
            try:
                verification_suite()
            except Exception as e:
                print(f"❌ Error in verification suite {verification_suite.__name__}: {e}")
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print verification summary."""
        print("\n" + "=" * 70)
        print("📊 VERIFICATION SUMMARY")
        print("=" * 70)
        
        total_checks = len(self.results)
        passed_checks = sum(1 for r in self.results if r['status'] == 'PASS')
        failed_checks = sum(1 for r in self.results if r['status'] == 'FAIL')
        warning_checks = sum(1 for r in self.results if r['status'] == 'WARN')
        
        print(f"Total verification checks: {total_checks}")
        print(f"✅ Passed: {passed_checks}")
        print(f"❌ Failed: {failed_checks}")
        print(f"⚠️ Warnings: {warning_checks}")
        print(f"Success rate: {(passed_checks/total_checks*100):.1f}%" if total_checks > 0 else "0.0%")
        
        if failed_checks > 0:
            print(f"\n❌ FAILED CHECKS ({failed_checks}):")
            for result in self.results:
                if result['status'] == 'FAIL':
                    print(f"   {result['system']}: {result['details']}")
        
        if warning_checks > 0:
            print(f"\n⚠️ WARNINGS ({warning_checks}):")
            for result in self.results:
                if result['status'] == 'WARN':
                    print(f"   {result['system']}: {result['details']}")

if __name__ == "__main__":
    verifier = PerformanceVerifier()
    verifier.run_all_verifications()