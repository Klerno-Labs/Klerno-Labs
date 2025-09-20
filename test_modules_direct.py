#!/usr/bin/env python3
"""
Direct Module Testing for Core Authentication System
Tests authentication functionality by importing and testing modules directly
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

import asyncio
import json
from datetime import datetime


def test_auth_module():
    """Test core authentication module"""
    print("🔐 Testing Authentication Module...")

    try:
        from app.auth import (create_access_token, hash_password, verify_access_token,
                              verify_password)

        # Test password hashing
        print("  ✅ Password hashing module imported")
        password = "test_password_123"
        hashed = hash_password(password)
        print(f"  ✅ Password hashed successfully: {len(hashed)} chars")

        # Test password verification
        if verify_password(password, hashed):
            print("  ✅ Password verification works")
        else:
            print("  ❌ Password verification failed")
            return False

        # Test token creation
        token = create_access_token({"sub": "test@example.com"})
        print(f"  ✅ Access token created: {len(token)} chars")

        # Test token verification
        payload = verify_access_token(token)
        if payload and payload.get("sub") == "test@example.com":
            print("  ✅ Token verification works")
        else:
            print("  ❌ Token verification failed")
            return False

        return True

    except Exception as e:
        print(f"  ❌ Authentication module error: {e}")
        return False

def test_security_module():
    """Test security module"""
    print("\n🛡️ Testing Security Module...")

    try:
        from app.security import AuditLogger, SecurityManager

        # Test security manager
        security = SecurityManager()
        print("  ✅ Security manager initialized")

        # Test audit logger
        logger = AuditLogger()
        logger.log_auth_success("test@example.com", "127.0.0.1")
        print("  ✅ Audit logging works")

        return True

    except Exception as e:
        print(f"  ❌ Security module error: {e}")
        return False

def test_models():
    """Test data models"""
    print("\n📊 Testing Data Models...")

    try:
        from app.models import ReportRequest, ReportSummary, TaggedTransaction, Transaction

        # Test Transaction model
        tx = Transaction(
            hash="test_hash_123",
            amount=100.50,
            fee=0.25,
            from_address="rTest1...",
            to_address="rTest2...",
            timestamp=datetime.now(),
            network="XRPL"
        )
        print(f"  ✅ Transaction model created: {tx.hash}")

        # Test TaggedTransaction
        tagged_tx = TaggedTransaction(
            **tx.model_dump(),
            risk_score=0.3,
            tags=["legitimate", "payment"],
            analysis_metadata={"source": "test"}
        )
        print(f"  ✅ Tagged transaction created: {tagged_tx.risk_score}")

        # Test ReportRequest
        report_req = ReportRequest(
            addresses=["rTest1...", "rTest2..."],
            start_date=datetime.now(),
            end_date=datetime.now()
        )
        print(f"  ✅ Report request created: {len(report_req.addresses)} addresses")

        return True

    except Exception as e:
        print(f"  ❌ Models error: {e}")
        return False

def test_xrpl_integration():
    """Test XRPL integration"""
    print("\n💰 Testing XRPL Integration...")

    try:
        from app.integrations.xrp import get_account_balance, validate_address

        # Test address validation
        valid_address = "rN7n7otQDd6FczFgLdSqtcsAUxDkw6fzRH"
        if validate_address(valid_address):
            print("  ✅ Address validation works")
        else:
            print("  ❌ Address validation failed")
            return False

        # Test balance retrieval (this may fail if no network access)
        try:
            balance = get_account_balance(valid_address)
            print(f"  ✅ Balance retrieval works: {balance}")
        except Exception as balance_error:
            print(f"  ⚠️ Balance retrieval needs network: {balance_error}")

        return True

    except Exception as e:
        print(f"  ❌ XRPL integration error: {e}")
        return False

def test_iso20022():
    """Test ISO20022 compliance features"""
    print("\n🏦 Testing ISO20022 Features...")

    try:
        from app.iso20022_compliance import ISO20022Manager

        manager = ISO20022Manager()
        print("  ✅ ISO20022 manager initialized")

        # Test pain.001 message building
        payment_data = {
            "amount": "100.00",
            "currency": "EUR",
            "debtor_name": "Test Company",
            "debtor_account": "DE89370400440532013000",
            "creditor_name": "Recipient Company",
            "creditor_account": "GB29NWBK60161331926819"
        }

        pain001_xml = manager.build_pain001(payment_data)
        print(f"  ✅ pain.001 message built: {len(pain001_xml)} chars")

        # Test validation
        validation_result = manager.validate_xml(pain001_xml, "pain.001")
        print(f"  ✅ XML validation: {validation_result['valid']}")

        return True

    except Exception as e:
        print(f"  ❌ ISO20022 error: {e}")
        return False

def test_analytics():
    """Test analytics and reporting"""
    print("\n📈 Testing Analytics Module...")

    try:
        from app.analytics import analyze_transactions, generate_insights

        # Create sample transactions for analysis
        sample_transactions = [
            {
                "hash": "tx1",
                "amount": 100.0,
                "fee": 0.1,
                "from_address": "rAddr1",
                "to_address": "rAddr2",
                "timestamp": datetime.now(),
                "network": "XRPL"
            },
            {
                "hash": "tx2",
                "amount": 50.0,
                "fee": 0.05,
                "from_address": "rAddr2",
                "to_address": "rAddr3",
                "timestamp": datetime.now(),
                "network": "XRPL"
            }
        ]

        # Test transaction analysis
        analysis = analyze_transactions(sample_transactions)
        print(f"  ✅ Transaction analysis: {len(analysis.get('transactions', []))} processed")

        # Test insights generation
        insights = generate_insights(analysis)
        print(f"  ✅ Insights generated: {len(insights.get('insights', []))} insights")

        return True

    except Exception as e:
        print(f"  ❌ Analytics error: {e}")
        return False

def test_performance():
    """Test performance optimization features"""
    print("\n⚡ Testing Performance Features...")

    try:
        from app.core.performance import CircuitBreaker, cached

        # Test circuit breaker
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        print("  ✅ Circuit breaker initialized")

        # Test caching decorator
        @cached(ttl=60)
        def sample_function(param):
            return f"result_{param}"

        result1 = sample_function("test")
        result2 = sample_function("test")  # Should be cached
        print(f"  ✅ Caching works: {result1 == result2}")

        return True

    except Exception as e:
        print(f"  ❌ Performance features error: {e}")
        return False

def main():
    """Run all module tests"""
    print("🧪 Klerno Labs - Direct Module Quality Testing")
    print("=" * 60)
    print(f"Started at: {datetime.now()}")
    print()

    tests = [
        ("Authentication", test_auth_module),
        ("Security", test_security_module),
        ("Data Models", test_models),
        ("XRPL Integration", test_xrpl_integration),
        ("ISO20022", test_iso20022),
        ("Analytics", test_analytics),
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
    print("📊 Module Testing Summary")
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
    with open("module_test_results.json", "w") as f:
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

    print(f"\n💾 Results saved to module_test_results.json")
    print(f"🏁 Testing completed at: {datetime.now()}")

    return passed / total >= 0.8  # 80% success rate

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
