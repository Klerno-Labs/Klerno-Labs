"""
Simple test for enterprise components
"""
import asyncio
import sys
import traceback
from pathlib import Path

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

async def test_enterprise_components():
    """Test each enterprise component individually"""
    
    print("🧪 TESTING ENTERPRISE COMPONENTS")
    print("=" * 50)
    
    # Test 1: Database System
    try:
        from app.enterprise_database_async import get_database_manager
        db_manager = get_database_manager()
        await db_manager.initialize()
        result = await db_manager.execute_query("SELECT 'Database OK' as status")
        print("✅ Database System: WORKING")
    except Exception as e:
        print(f"❌ Database System: ERROR - {e}")
        traceback.print_exc()
    
    # Test 2: Error Handler
    try:
        from app.enterprise_error_handling import get_error_handler
        error_handler = get_error_handler()
        stats = error_handler.get_error_statistics()
        print("✅ Error Handler: WORKING")
    except Exception as e:
        print(f"❌ Error Handler: ERROR - {e}")
        traceback.print_exc()
    
    # Test 3: Health Monitor
    try:
        from app.enterprise_health_dashboard import get_health_monitor
        health_monitor = get_health_monitor()
        health_data = health_monitor.get_dashboard_data()
        print("✅ Health Monitor: WORKING")
    except Exception as e:
        print(f"❌ Health Monitor: ERROR - {e}")
        traceback.print_exc()
    
    # Test 4: Analytics System
    try:
        from app.enterprise_analytics_reporting import get_analytics_system
        analytics = get_analytics_system()
        event_id = analytics.track_event("test_event")
        print("✅ Analytics System: WORKING")
    except Exception as e:
        print(f"❌ Analytics System: ERROR - {e}")
        traceback.print_exc()
    
    # Test 5: CI/CD Pipeline
    try:
        from app.enterprise_cicd_pipeline import CICDPipeline
        cicd = CICDPipeline()
        config = cicd.get_pipeline_config()
        print("✅ CI/CD Pipeline: WORKING")
    except Exception as e:
        print(f"❌ CI/CD Pipeline: ERROR - {e}")
        traceback.print_exc()
    
    print("\n🎯 COMPONENT TESTING COMPLETE")

if __name__ == "__main__":
    asyncio.run(test_enterprise_components())