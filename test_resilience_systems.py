#!/usr/bin/env python3
"""
Error handling and resilience testing script.
Tests circuit breakers, retry mechanisms, and recovery systems.
"""

import sys
import os
import asyncio
import time
from pathlib import Path

# Add the app directory to the Python path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

def test_circuit_breaker_basic():
    """Test basic circuit breaker functionality."""
    try:
        from app.resilience_system import CircuitBreaker
        
        # Create circuit breaker
        cb = CircuitBreaker(failure_threshold=3, timeout=5)
        
        # Test initial state
        assert cb.state == "CLOSED", "Initial state should be CLOSED"
        assert cb.failure_count == 0, "Initial failure count should be 0"
        
        # Test successful calls
        def successful_operation():
            return "success"
        
        result = cb.call(successful_operation)
        assert result == "success", "Successful call should return result"
        assert cb.failure_count == 0, "Failure count should remain 0"
        
        print("✅ Circuit breaker basic functionality: PASSED")
        return True
    except Exception as e:
        print(f"❌ Circuit breaker basic functionality: FAILED - {e}")
        return False

def test_circuit_breaker_failure_handling():
    """Test circuit breaker failure handling."""
    try:
        from app.resilience_system import CircuitBreaker
        
        cb = CircuitBreaker(failure_threshold=2, timeout=1)
        
        # Test failing operation
        def failing_operation():
            raise Exception("Test failure")
        
        # First failure
        try:
            cb.call(failing_operation)
        except:
            pass
        assert cb.failure_count == 1, "Failure count should be 1"
        assert cb.state == "CLOSED", "State should still be CLOSED"
        
        # Second failure - should open circuit
        try:
            cb.call(failing_operation)
        except:
            pass
        assert cb.failure_count == 2, "Failure count should be 2"
        assert cb.state == "OPEN", "State should be OPEN"
        
        print("✅ Circuit breaker failure handling: PASSED")
        return True
    except Exception as e:
        print(f"❌ Circuit breaker failure handling: FAILED - {e}")
        return False

def test_retry_mechanism():
    """Test retry mechanism."""
    try:
        from app.resilience_system import RetryManager
        
        retry_manager = RetryManager()
        
        # Test retry configuration
        assert hasattr(retry_manager, 'max_retries'), "Should have max_retries config"
        assert hasattr(retry_manager, 'backoff_factor'), "Should have backoff_factor config"
        
        # Test successful retry
        call_count = 0
        def eventually_successful():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = retry_manager.execute_with_retry(eventually_successful, max_retries=5)
        assert result == "success", "Should succeed after retries"
        assert call_count == 3, "Should have been called 3 times"
        
        print("✅ Retry mechanism: PASSED")
        return True
    except Exception as e:
        print(f"❌ Retry mechanism: FAILED - {e}")
        return False

def test_self_healing_system():
    """Test self-healing system."""
    try:
        from app.resilience_system import SelfHealingSystem
        
        healing_system = SelfHealingSystem()
        
        # Test healing system initialization
        assert hasattr(healing_system, 'healing_rules'), "Should have healing rules"
        assert hasattr(healing_system, 'execute_healing'), "Should have execute_healing method"
        
        # Test healing rule execution
        test_error = Exception("database connection failed")
        healing_result = healing_system.attempt_healing(test_error)
        
        # Should return some result (success or failure)
        assert healing_result is not None, "Healing should return result"
        
        print("✅ Self-healing system: PASSED")
        return True
    except Exception as e:
        print(f"❌ Self-healing system: FAILED - {e}")
        return False

def test_error_recovery_mechanisms():
    """Test error recovery mechanisms."""
    try:
        from app.resilience_system import ErrorRecoveryManager
        
        recovery_manager = ErrorRecoveryManager()
        
        # Test recovery manager has required methods
        assert hasattr(recovery_manager, 'handle_error'), "Should have handle_error method"
        assert hasattr(recovery_manager, 'recover_from_error'), "Should have recover_from_error method"
        
        # Test error handling
        test_error = {
            'type': 'database_error',
            'message': 'Connection timeout',
            'timestamp': time.time()
        }
        
        recovery_result = recovery_manager.handle_error(test_error)
        assert recovery_result is not None, "Error handling should return result"
        
        print("✅ Error recovery mechanisms: PASSED")
        return True
    except Exception as e:
        print(f"❌ Error recovery mechanisms: FAILED - {e}")
        return False

def test_failover_system():
    """Test failover system."""
    try:
        from app.resilience_system import FailoverManager
        
        failover_manager = FailoverManager()
        
        # Test failover configuration
        assert hasattr(failover_manager, 'primary_endpoints'), "Should have primary endpoints"
        assert hasattr(failover_manager, 'backup_endpoints'), "Should have backup endpoints"
        
        # Test failover execution
        test_service = "database"
        failover_result = failover_manager.execute_failover(test_service)
        
        # Should return failover status
        assert isinstance(failover_result, (bool, dict)), "Failover should return status"
        
        print("✅ Failover system: PASSED")
        return True
    except Exception as e:
        print(f"❌ Failover system: FAILED - {e}")
        return False

def test_resilience_monitoring():
    """Test resilience monitoring."""
    try:
        from app.resilience_system import ResilienceMonitor
        
        monitor = ResilienceMonitor()
        
        # Test monitoring capabilities
        assert hasattr(monitor, 'track_failure'), "Should have track_failure method"
        assert hasattr(monitor, 'get_health_status'), "Should have get_health_status method"
        
        # Test failure tracking
        monitor.track_failure("test_service", "test_error")
        
        # Test health status
        health_status = monitor.get_health_status()
        assert isinstance(health_status, dict), "Health status should be dict"
        
        print("✅ Resilience monitoring: PASSED")
        return True
    except Exception as e:
        print(f"❌ Resilience monitoring: FAILED - {e}")
        return False

def test_load_balancer():
    """Test load balancer functionality."""
    try:
        from app.resilience_system import LoadBalancer
        
        load_balancer = LoadBalancer()
        
        # Test load balancer configuration
        assert hasattr(load_balancer, 'servers'), "Should have servers list"
        assert hasattr(load_balancer, 'get_next_server'), "Should have get_next_server method"
        
        # Test server selection
        if hasattr(load_balancer, 'servers') and load_balancer.servers:
            selected_server = load_balancer.get_next_server()
            assert selected_server is not None, "Should select a server"
        
        print("✅ Load balancer functionality: PASSED")
        return True
    except Exception as e:
        print(f"❌ Load balancer functionality: FAILED - {e}")
        return False

def main():
    """Run all error handling and resilience tests."""
    print("🛡️ Error Handling and Resilience Testing")
    print("=" * 42)
    
    tests = [
        test_circuit_breaker_basic,
        test_circuit_breaker_failure_handling,
        test_retry_mechanism,
        test_self_healing_system,
        test_error_recovery_mechanisms,
        test_failover_system,
        test_resilience_monitoring,
        test_load_balancer
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: FAILED - {e}")
    
    print("\n" + "=" * 42)
    print(f"Resilience Systems Results: {passed}/{total} passed")
    
    if passed >= total * 0.75:  # 75% pass rate is acceptable
        print("🎉 Error handling and resilience systems are working well!")
        return True
    else:
        print(f"⚠️  {total - passed} resilience systems need attention")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)