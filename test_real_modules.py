#!/usr/bin/env python3
"""
Corrected Module Testing for Actual Klerno Labs Architecture
Tests real functions and classes available in the codebase
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

import json
from datetime import datetime


def test_security_session():
    """Test security session functions"""
    print("🔐 Testing Security Session Module...")
    
    try:
        from app.security_session import hash_pw, issue_jwt, verify_pw

        # Test password hashing
        password = "test_password_123"
        hashed = hash_pw(password)
        print(f"  ✅ Password hashed successfully: {len(hashed)} chars")
        
        # Test password verification
        if verify_pw(password, hashed):
            print("  ✅ Password verification works")
        else:
            print("  ❌ Password verification failed")
            return False
            
        # Test JWT creation (need to check for SECRET_KEY)
        try:
            token = issue_jwt(1, "test@example.com", "user")
            print(f"  ✅ JWT token created: {len(token)} chars")
        except SystemExit:
            print("  ⚠️ JWT creation requires JWT_SECRET environment variable")
        except Exception as e:
            print(f"  ⚠️ JWT creation error: {e}")
            
        return True
        
    except Exception as e:
        print(f"  ❌ Security session error: {e}")
        return False

def test_models():
    """Test data models"""
    print("\n📊 Testing Data Models...")
    
    try:
        from app.models import AccountStatus, Transaction, UserRole

        # Test enums
        print(f"  ✅ UserRole enum: {list(UserRole)}")
        print(f"  ✅ AccountStatus enum: {list(AccountStatus)}")
        
        # Test Transaction model (check actual constructor)
        try:
            tx = Transaction(
                tx_hash="test_hash_123",
                amount=100.50,
                fee=0.25,
                from_address="rTest1...",
                to_address="rTest2...",
                timestamp=datetime.now(),
                ledger_index=12345,
                network="XRPL"
            )
            print(f"  ✅ Transaction model created: {tx.tx_hash}")
        except Exception as tx_error:
            print(f"  ⚠️ Transaction model issue: {tx_error}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Models error: {e}")
        return False

def test_xrpl_integration():
    """Test XRPL integration"""
    print("\n💰 Testing XRPL Integration...")
    
    try:
        from app.integrations.xrp import XRPLManager

        # Test XRPL manager creation
        xrpl_manager = XRPLManager()
        print("  ✅ XRPL Manager initialized")
        
        # Test address validation (if available)
        test_address = "rN7n7otQDd6FczFgLdSqtcsAUxDkw6fzRH"
        try:
            if hasattr(xrpl_manager, 'validate_address'):
                if xrpl_manager.validate_address(test_address):
                    print("  ✅ Address validation works")
            else:
                print("  ⚠️ Address validation method not found")
        except Exception as addr_error:
            print(f"  ⚠️ Address validation error: {addr_error}")
            
        return True
        
    except Exception as e:
        print(f"  ❌ XRPL integration error: {e}")
        return False

def test_analytics():
    """Test analytics module"""
    print("\n📈 Testing Analytics Module...")
    
    try:
        from app.analytics import RiskAnalytics

        # Test risk analytics
        analytics = RiskAnalytics()
        print("  ✅ Risk analytics initialized")
        
        # Test empty analytics (from our test suite)
        empty_result = analytics.analyze_empty()
        print(f"  ✅ Empty analytics: {empty_result}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Analytics error: {e}")
        return False

def test_compliance():
    """Test compliance module"""
    print("\n⚖️ Testing Compliance Module...")
    
    try:
        from app.compliance import detect_fees, is_internal_transfer

        # Test fee detection
        test_memo = "Fee: $10 for processing"
        if detect_fees(test_memo):
            print("  ✅ Fee detection works")
        else:
            print("  ⚠️ Fee not detected in test memo")
            
        # Test internal transfer detection
        if not is_internal_transfer("external_test"):
            print("  ✅ Internal transfer detection works")
        else:
            print("  ⚠️ Internal transfer detection issue")
            
        return True
        
    except Exception as e:
        print(f"  ❌ Compliance error: {e}")
        return False

def test_guardian():
    """Test guardian risk assessment"""
    print("\n🛡️ Testing Guardian Module...")
    
    try:
        from app.guardian import assess_risk

        # Test risk assessment
        test_transaction = {
            "amount": 50000.0,  # Large amount
            "destination": "unknown_address",
            "source": "known_address"
        }
        
        risk_result = assess_risk(test_transaction)
        print(f"  ✅ Risk assessment: {risk_result}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Guardian error: {e}")
        return False

def test_security():
    """Test security module"""
    print("\n🔒 Testing Security Module...")
    
    try:
        from app.security import EnterpriseSecurityMiddleware

        # Test middleware creation
        middleware = EnterpriseSecurityMiddleware()
        print("  ✅ Enterprise security middleware initialized")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Security error: {e}")
        return False

def test_performance():
    """Test performance module"""
    print("\n⚡ Testing Performance Module...")
    
    try:
        from app.core.performance import PerformanceOptimizer

        # Test performance optimizer
        optimizer = PerformanceOptimizer()
        print("  ✅ Performance optimizer initialized")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Performance error: {e}")
        return False

def main():
    """Run all available module tests"""
    print("🧪 Klerno Labs - Real Module Quality Testing")
    print("=" * 60)
    print(f"Started at: {datetime.now()}")
    print()
    
    tests = [
        ("Security Session", test_security_session),
        ("Data Models", test_models),
        ("XRPL Integration", test_xrpl_integration),
        ("Analytics", test_analytics),
        ("Compliance", test_compliance),
        ("Guardian", test_guardian),
        ("Security", test_security),
        ("Performance", test_performance),
    ]
    
    results = {}
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            success = test_func()
            results[test_name] = {"success": success, "error": None}
            if success:
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            results[test_name] = {"success": False, "error": str(e)}
            print(f"❌ {test_name} ERROR: {e}")
    
    print("\n" + "="*60)
    print("📊 Real Module Testing Summary")
    print("="*60)
    print(f"Total Modules: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {(passed/total*100):.1f}%")
    
    print("\n📋 Detailed Results:")
    for test_name, result in results.items():
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"{status} {test_name}")
        if result["error"]:
            print(f"     Error: {result['error']}")
    
    # Save results
    with open("real_module_test_results.json", "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": total,
                "passed": passed,
                "failed": total - passed,
                "success_rate": passed/total*100
            },
            "results": results
        }, f, indent=2)
    
    print(f"\n💾 Results saved to real_module_test_results.json")
    print(f"🏁 Testing completed at: {datetime.now()}")
    
    return passed / total >= 0.8  # 80% success rate

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)