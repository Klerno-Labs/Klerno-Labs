"""
Klerno Labs Enterprise Startup System
Complete enterprise-grade application launcher with all systems
"""
import asyncio
import logging
import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

# Import enterprise systems
try:
    from app.enterprise_integration_hub import initialize_enterprise, get_enterprise_hub
    from app.enterprise_database_async import get_database_manager
    from app.enterprise_error_handling import get_error_handler
    from app.enterprise_cicd_pipeline import CICDPipeline
    from app.enterprise_health_dashboard import get_health_monitor
    from app.enterprise_analytics_reporting import get_analytics_system
except ImportError as e:
    print(f"❌ Failed to import enterprise systems: {e}")
    sys.exit(1)

# Configure enterprise logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./data/enterprise.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class EnterpriseStartup:
    """Enterprise application startup orchestrator"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.hub = None
        self.systems_status = {}
        
    async def start_enterprise(self):
        """Start complete enterprise system"""
        
        print("🚀 KLERNO LABS ENTERPRISE SYSTEM STARTUP")
        print("=" * 60)
        print(f"⏰ Startup Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🖥️  Platform: {sys.platform}")
        print(f"🐍 Python Version: {sys.version}")
        print("=" * 60)
        
        try:
            # Create data directory
            Path("./data").mkdir(exist_ok=True)
            print("📁 Data directory ready")
            
            # Initialize enterprise hub
            print("\n🔧 INITIALIZING ENTERPRISE SYSTEMS...")
            print("-" * 40)
            
            self.hub = await initialize_enterprise()
            
            if not self.hub:
                print("❌ Enterprise initialization failed!")
                return False
            
            # Verify all systems
            print("\n🔍 VERIFYING SYSTEM STATUS...")
            print("-" * 40)
            
            status_ok = await self._verify_systems()
            
            if status_ok:
                print("\n✅ ENTERPRISE SYSTEM FULLY OPERATIONAL!")
                print("=" * 60)
                
                # Display system summary
                await self._display_system_summary()
                
                # Run demo operations
                await self._run_demo_operations()
                
                print("\n🎯 ENTERPRISE READY FOR PRODUCTION!")
                print("💡 Access dashboard at: http://localhost:8000/enterprise/dashboard")
                print("📊 Health monitoring: http://localhost:8000/health")
                print("📈 Analytics: http://localhost:8000/analytics")
                print("🔧 CI/CD Pipeline: http://localhost:8000/cicd")
                
                return True
            else:
                print("\n❌ System verification failed!")
                return False
                
        except Exception as e:
            logger.error(f"Enterprise startup failed: {e}")
            print(f"\n❌ STARTUP FAILED: {e}")
            return False
    
    async def _verify_systems(self):
        """Verify all enterprise systems are operational"""
        
        systems_to_check = [
            ("Database Manager", self._check_database),
            ("Error Handler", self._check_error_handler),
            ("Health Monitor", self._check_health_monitor),
            ("Analytics System", self._check_analytics),
            ("CI/CD Pipeline", self._check_cicd),
            ("Integration Hub", self._check_integration_hub)
        ]
        
        all_ok = True
        
        for system_name, check_func in systems_to_check:
            try:
                status = await check_func()
                if status:
                    print(f"✅ {system_name}: OPERATIONAL")
                    self.systems_status[system_name] = "OK"
                else:
                    print(f"❌ {system_name}: FAILED")
                    self.systems_status[system_name] = "FAILED"
                    all_ok = False
            except Exception as e:
                print(f"⚠️  {system_name}: ERROR - {e}")
                self.systems_status[system_name] = f"ERROR: {e}"
                all_ok = False
        
        return all_ok
    
    async def _check_database(self):
        """Check database system"""
        try:
            db_manager = get_database_manager()
            if db_manager:
                # Test query
                result = await db_manager.execute_query("SELECT 1 as test")
                return result is not None
            return False
        except Exception:
            return False
    
    async def _check_error_handler(self):
        """Check error handler"""
        try:
            error_handler = get_error_handler()
            if error_handler:
                # Test error handling
                stats = error_handler.get_error_statistics()
                return isinstance(stats, dict)
            return False
        except Exception:
            return False
    
    async def _check_health_monitor(self):
        """Check health monitor"""
        try:
            health_monitor = get_health_monitor()
            if health_monitor:
                # Test health check
                data = health_monitor.get_dashboard_data()
                return isinstance(data, dict)
            return False
        except Exception:
            return False
    
    async def _check_analytics(self):
        """Check analytics system"""
        try:
            analytics = get_analytics_system()
            if analytics:
                # Test analytics tracking
                event_id = analytics.track_event("startup_test")
                return event_id is not None
            return False
        except Exception:
            return False
    
    async def _check_cicd(self):
        """Check CI/CD pipeline"""
        try:
            cicd = CICDPipeline()
            if cicd:
                # Test pipeline validation
                config = cicd.get_pipeline_config()
                return isinstance(config, dict)
            return False
        except Exception:
            return False
    
    async def _check_integration_hub(self):
        """Check integration hub"""
        try:
            if self.hub and self.hub.is_running:
                # Test dashboard access
                dashboard = self.hub.get_enterprise_dashboard()
                return isinstance(dashboard, dict)
            return False
        except Exception:
            return False
    
    async def _display_system_summary(self):
        """Display comprehensive system summary"""
        
        dashboard = self.hub.get_enterprise_dashboard()
        
        print("\n📊 SYSTEM SUMMARY")
        print("-" * 40)
        print(f"🕐 Uptime: {dashboard.get('uptime_seconds', 0):.1f} seconds")
        print(f"⚙️  Active Systems: {len([s for s in self.systems_status.values() if s == 'OK'])}/6")
        
        # System status
        system_status = dashboard.get('system_status', {})
        for name, status in system_status.items():
            health = status.get('health_score', 0)
            print(f"   {name}: {health:.1f}% health")
        
        # Performance metrics
        perf_metrics = dashboard.get('performance_metrics', {})
        if perf_metrics:
            print("\n📈 PERFORMANCE METRICS")
            print("-" * 40)
            for system, metrics in perf_metrics.items():
                print(f"   {system}:")
                for metric, value in metrics.items():
                    print(f"     {metric}: {value}")
    
    async def _run_demo_operations(self):
        """Run demonstration operations"""
        
        print("\n🎬 RUNNING DEMO OPERATIONS...")
        print("-" * 40)
        
        try:
            # Test database operation
            print("🔹 Testing database operation...")
            db_result = await self.hub.execute_enterprise_operation(
                "database_query",
                {"query": "SELECT 'Enterprise System Online' as message"}
            )
            if db_result.get('status') == 'success':
                print("   ✅ Database operation successful")
            
            # Test health check
            print("🔹 Testing health check...")
            health_result = await self.hub.execute_enterprise_operation(
                "health_check",
                {}
            )
            if health_result.get('status') == 'success':
                print("   ✅ Health check successful")
            
            # Test analytics report
            print("🔹 Testing analytics report...")
            analytics = get_analytics_system()
            if analytics:
                report = analytics.generate_report("daily_summary")
                if report.get('status') == 'success':
                    print("   ✅ Analytics report generated")
            
            # Track startup completion
            analytics = get_analytics_system()
            if analytics:
                analytics.track_event(
                    "enterprise_startup_complete",
                    properties={
                        "startup_duration": (datetime.now() - self.start_time).total_seconds(),
                        "systems_count": len(self.systems_status),
                        "demo_operations": 3
                    }
                )
            
            print("   ✅ All demo operations completed")
            
        except Exception as e:
            print(f"   ⚠️  Demo operations error: {e}")
    
    async def run_interactive_mode(self):
        """Run interactive enterprise management mode"""
        
        print("\n" + "=" * 60)
        print("🖥️  ENTERPRISE INTERACTIVE MODE")
        print("=" * 60)
        print("Available commands:")
        print("  dashboard  - Show enterprise dashboard")
        print("  health     - Show health status")
        print("  analytics  - Show analytics summary")
        print("  metrics    - Show performance metrics")
        print("  test       - Run system tests")
        print("  shutdown   - Shutdown enterprise system")
        print("  help       - Show this help")
        print("=" * 60)
        
        while self.hub and self.hub.is_running:
            try:
                command = input("\n[ENTERPRISE]> ").strip().lower()
                
                if command == "dashboard":
                    await self._show_dashboard()
                elif command == "health":
                    await self._show_health_status()
                elif command == "analytics":
                    await self._show_analytics()
                elif command == "metrics":
                    await self._show_metrics()
                elif command == "test":
                    await self._run_system_tests()
                elif command == "shutdown":
                    await self._shutdown_enterprise()
                    break
                elif command == "help":
                    print("Available commands: dashboard, health, analytics, metrics, test, shutdown, help")
                elif command == "":
                    continue
                else:
                    print(f"Unknown command: {command}. Type 'help' for available commands.")
                    
            except KeyboardInterrupt:
                print("\n\n🛑 Shutdown requested...")
                await self._shutdown_enterprise()
                break
            except Exception as e:
                print(f"Command error: {e}")
    
    async def _show_dashboard(self):
        """Show enterprise dashboard"""
        dashboard = self.hub.get_enterprise_dashboard()
        print("\n📊 ENTERPRISE DASHBOARD")
        print("-" * 40)
        print(json.dumps(dashboard, indent=2, default=str))
    
    async def _show_health_status(self):
        """Show health status"""
        health_monitor = get_health_monitor()
        if health_monitor:
            health_data = health_monitor.get_dashboard_data()
            print("\n🏥 HEALTH STATUS")
            print("-" * 40)
            print(json.dumps(health_data, indent=2, default=str))
    
    async def _show_analytics(self):
        """Show analytics summary"""
        analytics = get_analytics_system()
        if analytics:
            analytics_data = analytics.get_analytics_dashboard()
            print("\n📈 ANALYTICS SUMMARY")
            print("-" * 40)
            print(json.dumps(analytics_data, indent=2, default=str))
    
    async def _show_metrics(self):
        """Show performance metrics"""
        dashboard = self.hub.get_enterprise_dashboard()
        metrics = dashboard.get('performance_metrics', {})
        print("\n⚡ PERFORMANCE METRICS")
        print("-" * 40)
        print(json.dumps(metrics, indent=2, default=str))
    
    async def _run_system_tests(self):
        """Run comprehensive system tests"""
        print("\n🧪 RUNNING SYSTEM TESTS...")
        print("-" * 40)
        
        test_results = {}
        
        # Test database
        try:
            result = await self.hub.execute_enterprise_operation(
                "database_query",
                {"query": "SELECT datetime('now') as current_time"}
            )
            test_results['database'] = result.get('status') == 'success'
        except Exception as e:
            test_results['database'] = False
        
        # Test error handling
        try:
            error_handler = get_error_handler()
            stats = error_handler.get_error_statistics()
            test_results['error_handling'] = isinstance(stats, dict)
        except Exception:
            test_results['error_handling'] = False
        
        # Test analytics
        try:
            analytics = get_analytics_system()
            event_id = analytics.track_event("system_test")
            test_results['analytics'] = event_id is not None
        except Exception:
            test_results['analytics'] = False
        
        # Display results
        for system, passed in test_results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {system}: {status}")
        
        overall = all(test_results.values())
        print(f"\n🎯 Overall: {'✅ ALL TESTS PASSED' if overall else '❌ SOME TESTS FAILED'}")
    
    async def _shutdown_enterprise(self):
        """Shutdown enterprise system"""
        print("\n🛑 SHUTTING DOWN ENTERPRISE SYSTEM...")
        print("-" * 40)
        
        if self.hub:
            await self.hub.shutdown()
        
        print("✅ Enterprise system shutdown complete")

async def main():
    """Main enterprise startup function"""
    
    startup = EnterpriseStartup()
    
    # Start enterprise system
    success = await startup.start_enterprise()
    
    if success:
        # Run interactive mode
        await startup.run_interactive_mode()
    else:
        print("\n❌ Enterprise startup failed - exiting")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🛑 Enterprise system interrupted")
    except Exception as e:
        print(f"\n❌ Enterprise system error: {e}")
        sys.exit(1)