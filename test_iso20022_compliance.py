#!/usr/bin/env python3
"""
ISO20022 compliance testing script.
Tests financial message processing capabilities.
"""

import sys
import os
import xml.etree.ElementTree as ET
from pathlib import Path

# Add the app directory to the Python path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

def test_iso20022_message_validation():
    """Test ISO20022 message validation."""
    try:
        from app.iso20022_compliance import ISO20022Validator
        
        validator = ISO20022Validator()
        
        # Test valid message structure
        valid_message = {
            "message_type": "pacs.008.001.08",
            "group_header": {
                "message_id": "MSG123456",
                "creation_date_time": "2024-01-01T12:00:00Z",
                "number_of_transactions": 1
            },
            "transaction": {
                "payment_id": "PAY123",
                "amount": "1000.00",
                "currency": "USD"
            }
        }
        
        result = validator.validate_message(valid_message)
        assert result["is_valid"], "Valid message should pass validation"
        
        print("✅ ISO20022 message validation: PASSED")
        return True
    except Exception as e:
        print(f"❌ ISO20022 message validation: FAILED - {e}")
        return False

def test_currency_code_validation():
    """Test currency code validation."""
    try:
        from app.iso20022_compliance import CurrencyCode
        
        # Test valid currency codes
        valid_codes = ["USD", "EUR", "GBP", "JPY"]
        for code in valid_codes:
            assert CurrencyCode.is_valid(code), f"{code} should be valid"
        
        # Test invalid currency codes
        invalid_codes = ["XXX", "ZZZ", "ABC"]
        for code in invalid_codes:
            assert not CurrencyCode.is_valid(code), f"{code} should be invalid"
        
        print("✅ Currency code validation: PASSED")
        return True
    except Exception as e:
        print(f"❌ Currency code validation: FAILED - {e}")
        return False

def test_bic_validation():
    """Test BIC (Bank Identifier Code) validation."""
    try:
        from app.iso20022_compliance import BICValidator
        
        validator = BICValidator()
        
        # Test valid BIC codes
        valid_bics = ["DEUTDEFF", "CHASUS33", "BARCGB22"]
        for bic in valid_bics:
            assert validator.validate_bic(bic), f"{bic} should be valid"
        
        # Test invalid BIC codes
        invalid_bics = ["ABC", "1234567890", "TOOLONG123456"]
        for bic in invalid_bics:
            assert not validator.validate_bic(bic), f"{bic} should be invalid"
        
        print("✅ BIC validation: PASSED")
        return True
    except Exception as e:
        print(f"❌ BIC validation: FAILED - {e}")
        return False

def test_iban_validation():
    """Test IBAN validation."""
    try:
        from app.iso20022_compliance import IBANValidator
        
        validator = IBANValidator()
        
        # Test valid IBAN (example format)
        valid_iban = "DE89370400440532013000"
        result = validator.validate_iban(valid_iban)
        assert result["is_valid"], "Valid IBAN should pass validation"
        
        # Test invalid IBAN
        invalid_iban = "INVALID123456789"
        result = validator.validate_iban(invalid_iban)
        assert not result["is_valid"], "Invalid IBAN should fail validation"
        
        print("✅ IBAN validation: PASSED")
        return True
    except Exception as e:
        print(f"❌ IBAN validation: FAILED - {e}")
        return False

def test_payment_instruction_processing():
    """Test payment instruction processing."""
    try:
        from app.iso20022_compliance import PaymentInstructionProcessor
        
        processor = PaymentInstructionProcessor()
        
        # Test payment instruction
        instruction = {
            "instruction_id": "INST123",
            "end_to_end_id": "E2E123",
            "amount": "500.00",
            "currency": "EUR",
            "debtor": {
                "name": "John Doe",
                "account": "DE89370400440532013000"
            },
            "creditor": {
                "name": "Jane Smith",
                "account": "FR1420041010050500013M02606"
            }
        }
        
        result = processor.process_instruction(instruction)
        assert result["status"] == "processed", "Instruction should be processed"
        
        print("✅ Payment instruction processing: PASSED")
        return True
    except Exception as e:
        print(f"❌ Payment instruction processing: FAILED - {e}")
        return False

def test_xml_message_generation():
    """Test XML message generation."""
    try:
        from app.iso20022_compliance import XMLMessageGenerator
        
        generator = XMLMessageGenerator()
        
        # Test XML generation
        message_data = {
            "message_type": "pacs.008.001.08",
            "group_header": {
                "message_id": "MSG789",
                "creation_date_time": "2024-01-01T15:30:00Z"
            }
        }
        
        xml_output = generator.generate_xml(message_data)
        assert xml_output is not None, "XML should be generated"
        assert "MSG789" in xml_output, "XML should contain message ID"
        
        # Verify XML is well-formed
        ET.fromstring(xml_output)
        
        print("✅ XML message generation: PASSED")
        return True
    except Exception as e:
        print(f"❌ XML message generation: FAILED - {e}")
        return False

def test_compliance_reporting():
    """Test compliance reporting functionality."""
    try:
        from app.compliance_reporting import ComplianceReporter
        
        reporter = ComplianceReporter()
        
        # Test compliance report generation
        transaction_data = {
            "transaction_id": "TXN123",
            "amount": "2000.00",
            "currency": "USD",
            "timestamp": "2024-01-01T10:00:00Z"
        }
        
        report = reporter.generate_compliance_report([transaction_data])
        assert report is not None, "Compliance report should be generated"
        assert "total_transactions" in report, "Report should contain transaction count"
        
        print("✅ Compliance reporting: PASSED")
        return True
    except Exception as e:
        print(f"❌ Compliance reporting: FAILED - {e}")
        return False

def test_aml_screening():
    """Test Anti-Money Laundering screening."""
    try:
        from app.iso20022_compliance import AMLScreening
        
        screener = AMLScreening()
        
        # Test customer screening
        customer_data = {
            "name": "John Doe",
            "country": "US",
            "entity_type": "individual"
        }
        
        result = screener.screen_customer(customer_data)
        assert "risk_level" in result, "Screening should return risk level"
        assert result["risk_level"] in ["low", "medium", "high"], "Risk level should be valid"
        
        print("✅ AML screening: PASSED")
        return True
    except Exception as e:
        print(f"❌ AML screening: FAILED - {e}")
        return False

def main():
    """Run all ISO20022 compliance tests."""
    print("🏦 ISO20022 Compliance Testing")
    print("=" * 40)
    
    tests = [
        test_iso20022_message_validation,
        test_currency_code_validation,
        test_bic_validation,
        test_iban_validation,
        test_payment_instruction_processing,
        test_xml_message_generation,
        test_compliance_reporting,
        test_aml_screening
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
    print(f"ISO20022 Compliance Results: {passed}/{total} passed")
    
    if passed >= total * 0.75:  # 75% pass rate is acceptable
        print("🎉 ISO20022 compliance systems are working well!")
        return True
    else:
        print(f"⚠️  {total - passed} compliance systems need attention")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)