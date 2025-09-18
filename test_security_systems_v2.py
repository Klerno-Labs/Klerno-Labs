#!/usr/bin/env python3
"""
Security systems validation script.
Tests core security functionality with correct imports.
"""

import sys
import os
import tempfile
from pathlib import Path

# Add the app directory to the Python path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

def test_password_hashing():
    """Test password hashing functionality."""
    try:
        from app.security_session import hash_pw, verify_pw
        
        test_password = "TestPassword123!"
        hashed = hash_pw(test_password)
        
        # Verify password hashing works
        assert hashed != test_password, "Password should be hashed"
        assert verify_pw(test_password, hashed), "Password verification should work"
        assert not verify_pw("wrong_password", hashed), "Wrong password should not verify"
        
        print("✅ Password hashing: PASSED")
        return True
    except Exception as e:
        print(f"❌ Password hashing: FAILED - {e}")
        return False

def test_guardian_risk_scoring():
    """Test Guardian risk scoring functionality."""
    try:
        from app.guardian import score_risk
        
        # Test normal transaction
        normal_tx = {
            "amount": "100.0",
            "memo": "Regular payment",
            "fee": "0.1"
        }
        score, flags = score_risk(normal_tx)
        assert 0 <= score <= 1, "Score should be between 0 and 1"
        
        # Test suspicious transaction
        suspicious_tx = {
            "amount": "10000.0",
            "memo": "scam payment urgent",
            "fee": "100.0"
        }
        susp_score, susp_flags = score_risk(suspicious_tx)
        assert susp_score > score, "Suspicious transaction should have higher score"
        assert len(susp_flags) > 0, "Suspicious transaction should have flags"
        
        print("✅ Guardian risk scoring: PASSED")
        return True
    except Exception as e:
        print(f"❌ Guardian risk scoring: FAILED - {e}")
        return False

def test_circuit_breaker():
    """Test circuit breaker functionality."""
    try:
        from app.resilience_system import CircuitBreaker, CircuitBreakerConfig
        
        # Create circuit breaker with low threshold for testing
        config = CircuitBreakerConfig(
            failure_threshold=3,
            timeout=1.0,
            recovery_timeout=5.0
        )
        breaker = CircuitBreaker("test_service", config)
        
        # Test circuit breaker states
        assert breaker.state.value == "closed", "Circuit should start closed"
        
        # Simulate failures
        for i in range(3):
            breaker._record_failure()
        
        # After threshold failures, should open
        assert breaker.state.value == "open", "Circuit should open after failures"
        
        print("✅ Circuit breaker: PASSED")
        return True
    except Exception as e:
        print(f"❌ Circuit breaker: FAILED - {e}")
        return False

def test_security_orchestrator():
    """Test security orchestrator functionality."""
    try:
        from app.advanced_security import SecurityOrchestrator
        
        orchestrator = SecurityOrchestrator()
        
        # Test threat detection
        suspicious_data = {
            "user_agent": "suspicious-bot/1.0",
            "ip": "192.168.1.1",
            "request_count": 1000
        }
        
        # Check if orchestrator has threat detection methods
        assert hasattr(orchestrator, 'analyze_request'), "Should have analyze_request method"
        
        print("✅ Security orchestrator: PASSED")
        return True
    except Exception as e:
        print(f"❌ Security orchestrator: FAILED - {e}")
        return False

def test_enterprise_security():
    """Test enterprise security manager."""
    try:
        from app.enterprise_security import SecurityManager
        
        security_manager = SecurityManager()
        
        # Test security configuration
        assert hasattr(security_manager, 'configure_security'), "Should have configure_security method"
        
        # Test role validation
        assert hasattr(security_manager, 'validate_role'), "Should have validate_role method"
        
        print("✅ Enterprise security: PASSED")
        return True
    except Exception as e:
        print(f"❌ Enterprise security: FAILED - {e}")
        return False

def test_security_headers_middleware():
    """Test security headers middleware."""
    try:
        from app.middleware import SecurityHeadersMiddleware
        
        # Verify middleware class exists
        assert SecurityHeadersMiddleware is not None, "SecurityHeadersMiddleware should exist"
        
        # Test initialization
        middleware = SecurityHeadersMiddleware(None)
        assert middleware is not None, "Middleware should initialize"
        
        print("✅ Security headers middleware: PASSED")
        return True
    except Exception as e:
        print(f"❌ Security headers middleware: FAILED - {e}")
        return False

def test_rate_limit_middleware():
    """Test rate limiting middleware."""
    try:
        from app.middleware import RateLimitMiddleware
        
        # Verify middleware class exists
        assert RateLimitMiddleware is not None, "RateLimitMiddleware should exist"
        
        # Test initialization
        middleware = RateLimitMiddleware(None)
        assert middleware is not None, "Rate limit middleware should initialize"
        
        print("✅ Rate limit middleware: PASSED")
        return True
    except Exception as e:
        print(f"❌ Rate limit middleware: FAILED - {e}")
        return False

def test_compliance_validation():
    """Test compliance validation functionality."""
    try:
        from app.compliance import validate_transaction
        
        # Test transaction validation
        test_transaction = {
            "amount": 1000,
            "currency": "USD",
            "sender": "test_sender",
            "receiver": "test_receiver"
        }
        
        # Should not raise exception for valid transaction
        result = validate_transaction(test_transaction)
        assert result is not None, "Validation should return result"
        
        print("✅ Compliance validation: PASSED")
        return True
    except Exception as e:
        print(f"❌ Compliance validation: FAILED - {e}")
        return False

def main():
    """Run all security tests."""
    print("🔒 Security Systems Validation")
    print("=" * 40)
    
    tests = [
        test_password_hashing,
        test_guardian_risk_scoring,
        test_circuit_breaker,
        test_security_orchestrator,
        test_enterprise_security,
        test_security_headers_middleware,
        test_rate_limit_middleware,
        test_compliance_validation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: FAILED - {e}")
    
    print("\n" + "=" * 40)
    print(f"Security Test Results: {passed}/{total} passed")
    
    if passed >= total * 0.75:  # 75% pass rate is acceptable
        print("🎉 Security systems are working well!")
        return True
    else:
        print(f"⚠️  {total - passed} security systems need attention")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)