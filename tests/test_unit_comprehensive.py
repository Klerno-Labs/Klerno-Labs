"""Comprehensive Unit Tests
Tests individual components and functions in isolation
"""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import jwt
import pytest

from app.auth import create_access_token, verify_token
from app.compliance import ComplianceEngine, ComplianceTag
from app.guardian import GuardianEngine
from app.models import Transaction, User
from app.paywall import PaywallManager


class TestUserModel:
    """Test User model functionality."""

    def test_user_creation(self):
        """Test user object creation."""
        user = User(
            id=1,
            email="test@example.com",
            hashed_password="$2b$12$test_hash",
            is_active=True,
            is_admin=False,
        )

        assert user.id == 1
        assert user.email == "test@example.com"
        assert user.is_active is True
        assert user.is_admin is False

    def test_user_validation(self):
        """Test user data validation."""
        with pytest.raises(ValueError):
            User(
                id=1,
                email="invalid-email",  # Invalid email format
                hashed_password="hash",
                is_active=True,
                is_admin=False,
            )


class TestTransactionModel:
    """Test Transaction model functionality."""

    def test_transaction_creation(self):
        """Test transaction object creation."""
        transaction = Transaction(
            id=1,
            user_id=1,
            amount=Decimal("100.50"),
            currency="USD",
            status="completed",
        )

        assert transaction.id == 1
        assert transaction.user_id == 1
        assert transaction.amount == Decimal("100.50")
        assert transaction.currency == "USD"
        assert transaction.status == "completed"

    def test_transaction_amount_validation(self):
        """Test transaction amount validation."""
        with pytest.raises(ValueError):
            Transaction(
                id=1,
                user_id=1,
                amount=Decimal(-100),  # Negative amount
                currency="USD",
                status="completed",
            )


class TestAuthenticationSystem:
    """Test authentication and authorization."""

    def test_create_access_token(self):
        """Test JWT token creation."""
        user_data = {"sub": "test@example.com", "user_id": 1}
        token = create_access_token(data=user_data)

        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are typically longer

    def test_verify_token_valid(self):
        """Test token verification with valid token."""
        user_data = {"sub": "test@example.com", "user_id": 1}
        token = create_access_token(data=user_data)

        payload = verify_token(token)
        assert payload["sub"] == "test@example.com"
        assert payload["user_id"] == 1

    def test_verify_token_invalid(self):
        """Test token verification with invalid token."""
        with pytest.raises(jwt.PyJWTError):
            verify_token("invalid.jwt.token")

    def test_verify_token_expired(self):
        """Test token verification with expired token."""
        user_data = {"sub": "test@example.com", "user_id": 1}

        # Create token with very short expiration
        with patch("app.auth.ACCESS_TOKEN_EXPIRE_MINUTES", 0):
            token = create_access_token(data=user_data)

            # Wait for token to expire
            import time

            time.sleep(1)

            with pytest.raises(jwt.PyJWTError):
                verify_token(token)


class TestComplianceEngine:
    """Test compliance tagging and analysis."""

    @pytest.fixture
    def compliance_engine(self):
        """Create compliance engine for testing."""
        return ComplianceEngine()

    def test_compliance_tag_creation(self):
        """Test compliance tag object creation."""
        tag = ComplianceTag(
            transaction_id=1,
            tag_type="HIGH_RISK",
            confidence=0.85,
            details={"reason": "large_amount"},
        )

        assert tag.transaction_id == 1
        assert tag.tag_type == "HIGH_RISK"
        assert tag.confidence == 0.85
        assert tag.details["reason"] == "large_amount"

    @pytest.mark.asyncio
    async def test_analyze_transaction(self, compliance_engine):
        """Test transaction analysis."""
        transaction_data = {
            "amount": 50000,
            "currency": "USD",
            "from_account": "unknown",
            "to_account": "known_entity",
        }

        tags = await compliance_engine.analyze_transaction(transaction_data)

        assert isinstance(tags, list)
        assert len(tags) > 0
        assert all(isinstance(tag, ComplianceTag) for tag in tags)

    @pytest.mark.asyncio
    async def test_high_amount_detection(self, compliance_engine):
        """Test detection of high-amount transactions."""
        transaction_data = {
            "amount": 100000,  # High amount
            "currency": "USD",
            "from_account": "test_account",
            "to_account": "test_account_2",
        }

        tags = await compliance_engine.analyze_transaction(transaction_data)
        high_amount_tags = [tag for tag in tags if tag.tag_type == "HIGH_AMOUNT"]

        assert len(high_amount_tags) > 0
        assert high_amount_tags[0].confidence > 0.8


class TestGuardianEngine:
    """Test Guardian real-time monitoring."""

    @pytest.fixture
    def guardian_engine(self):
        """Create Guardian engine for testing."""
        return GuardianEngine()

    @pytest.mark.asyncio
    async def test_anomaly_detection(self, guardian_engine):
        """Test anomaly detection functionality."""
        transactions = [
            {"amount": 100, "timestamp": datetime.utcnow()},
            {"amount": 105, "timestamp": datetime.utcnow()},
            {"amount": 98, "timestamp": datetime.utcnow()},
            {"amount": 10000, "timestamp": datetime.utcnow()},  # Anomaly
        ]

        anomalies = await guardian_engine.detect_anomalies(transactions)

        assert len(anomalies) > 0
        assert anomalies[0]["amount"] == 10000

    @pytest.mark.asyncio
    async def test_pattern_recognition(self, guardian_engine):
        """Test pattern recognition in transactions."""
        transactions = [
            {"amount": 1000, "to_account": "account_a", "timestamp": datetime.utcnow()},
            {"amount": 1000, "to_account": "account_b", "timestamp": datetime.utcnow()},
            {"amount": 1000, "to_account": "account_c", "timestamp": datetime.utcnow()},
        ]

        patterns = await guardian_engine.analyze_patterns(transactions)

        assert len(patterns) > 0
        assert "structured_layering" in [p["type"] for p in patterns]


class TestPaywallManager:
    """Test paywall and subscription management."""

    @pytest.fixture
    def paywall_manager(self):
        """Create paywall manager for testing."""
        return PaywallManager()

    def test_subscription_validation(self, paywall_manager):
        """Test subscription status validation."""
        user_data = {
            "subscription_status": "active",
            "subscription_expires": datetime.utcnow() + timedelta(days=30),
        }

        is_valid = paywall_manager.validate_subscription(user_data)
        assert is_valid is True

    def test_expired_subscription(self, paywall_manager):
        """Test expired subscription handling."""
        user_data = {
            "subscription_status": "active",
            "subscription_expires": datetime.utcnow() - timedelta(days=1),
        }

        is_valid = paywall_manager.validate_subscription(user_data)
        assert is_valid is False

    def test_trial_period_calculation(self, paywall_manager):
        """Test trial period calculation."""
        signup_date = datetime.utcnow() - timedelta(days=5)
        trial_days_remaining = paywall_manager.calculate_trial_remaining(signup_date)

        assert trial_days_remaining == 25  # 30 - 5 = 25 days


class TestUtilityFunctions:
    """Test utility functions."""

    def test_currency_conversion(self):
        """Test currency conversion functionality."""
        from app.utils import convert_currency

        # Mock exchange rate
        with patch("app.utils.get_exchange_rate", return_value=1.2):
            result = convert_currency(100, "USD", "EUR")
            assert result == 120.0

    def test_data_validation(self):
        """Test data validation utilities."""
        from app.utils import validate_amount, validate_email

        assert validate_email("test@example.com") is True
        assert validate_email("invalid-email") is False

        assert validate_amount(Decimal("100.50")) is True
        assert validate_amount(Decimal(-50)) is False

    def test_encryption_functions(self):
        """Test encryption and decryption."""
        from app.security.encryption import decrypt_data, encrypt_data

        original_data = "sensitive information"
        encrypted = encrypt_data(original_data)
        decrypted = decrypt_data(encrypted)

        assert encrypted != original_data
        assert decrypted == original_data
