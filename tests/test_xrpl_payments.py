"""
Tests for XRPL payment processing.
"""
import pytest
from unittest.mock import patch, MagicMock
import uuid
from datetime import datetime, timedelta

from app.xrpl_payments import create_payment_request, verify_payment, get_payment_status
from app.subscriptions import SubscriptionTier
from tests.mocks.xrpl_client import MockXRPLClient


@pytest.fixture
def mock_xrpl_client():
    """Fixture to provide a mock XRPL client."""
    client = MockXRPLClient()
    client.connect()
    return client


@pytest.fixture
def test_user():
    """Fixture to provide a test user."""
    return {
        "id": "test_user_" + uuid.uuid4().hex[:8],
        "email": "test@example.com",
        "username": "testuser",
    }


@pytest.fixture
def test_destination_wallet():
    """Fixture for the destination wallet."""
    return "rPT1Sjq2YGrBMTttX4GZHjKu9dyfzbpAYe"


@pytest.fixture
def test_sender_wallet():
    """Fixture for a test sender wallet."""
    return "rSenderWalletAddressTestUser123"


class TestXRPLPayments:
    """Tests for XRPL payment functionality."""

    @patch('app.xrpl_payments.XRPLClient')
    def test_create_payment_request(self, mock_xrpl_class, test_user):
        """Test creating a payment request."""
        # Arrange
        mock_xrpl = mock_xrpl_class.return_value
        mock_xrpl.get_account_info.return_value = {"account_data": {"Account": "rDestination"}}
        
        # Act
        payment_info = create_payment_request(
            user_id=test_user["id"],
            tier=SubscriptionTier.PREMIUM
        )
        
        # Assert
        assert payment_info is not None
        assert payment_info.user_id == test_user["id"]
        assert payment_info.tier == SubscriptionTier.PREMIUM
        assert payment_info.destination_address is not None
        assert payment_info.amount_xrp > 0
        assert payment_info.memo.startswith("KL-")
        assert payment_info.expires_at > datetime.now()

    @patch('app.xrpl_payments.XRPLClient')
    def test_verify_valid_payment(self, mock_xrpl_class, test_user, test_destination_wallet, test_sender_wallet):
        """Test verifying a valid payment."""
        # Arrange
        mock_client = MockXRPLClient()
        mock_xrpl_class.return_value = mock_client
        
        # Create a payment request
        with patch('app.xrpl_payments.XRPLClient', return_value=mock_client):
            payment_info = create_payment_request(
                user_id=test_user["id"],
                tier=SubscriptionTier.BASIC
            )
        
        # Simulate the payment
        amount = 10.0  # Basic tier amount
        tx_hash = mock_client.simulate_payment(
            from_account=test_sender_wallet,
            to_account=test_destination_wallet,
            amount=amount,
            memo=payment_info.memo
        )
        
        # Act
        with patch('app.xrpl_payments.XRPLClient', return_value=mock_client):
            verification_result = verify_payment(tx_hash)
        
        # Assert
        assert verification_result.verified is True
        assert verification_result.user_id == test_user["id"]
        assert verification_result.tier == SubscriptionTier.BASIC
        assert float(verification_result.amount) == amount

    @patch('app.xrpl_payments.XRPLClient')
    def test_verify_invalid_amount(self, mock_xrpl_class, test_user, test_destination_wallet, test_sender_wallet):
        """Test verifying a payment with incorrect amount."""
        # Arrange
        mock_client = MockXRPLClient()
        mock_xrpl_class.return_value = mock_client
        
        # Create a payment request for Premium tier
        with patch('app.xrpl_payments.XRPLClient', return_value=mock_client):
            payment_info = create_payment_request(
                user_id=test_user["id"],
                tier=SubscriptionTier.PREMIUM
            )
        
        # Simulate payment with incorrect amount (too low)
        incorrect_amount = 5.0  # Less than any tier
        tx_hash = mock_client.simulate_payment(
            from_account=test_sender_wallet,
            to_account=test_destination_wallet,
            amount=incorrect_amount,
            memo=payment_info.memo
        )
        
        # Act
        with patch('app.xrpl_payments.XRPLClient', return_value=mock_client):
            verification_result = verify_payment(tx_hash)
        
        # Assert
        assert verification_result.verified is False
        assert "amount" in verification_result.reason.lower()

    @patch('app.xrpl_payments.XRPLClient')
    def test_verify_wrong_destination(self, mock_xrpl_class, test_user, test_sender_wallet):
        """Test verifying a payment sent to wrong destination."""
        # Arrange
        mock_client = MockXRPLClient()
        mock_xrpl_class.return_value = mock_client
        
        # Create a payment request
        with patch('app.xrpl_payments.XRPLClient', return_value=mock_client):
            payment_info = create_payment_request(
                user_id=test_user["id"],
                tier=SubscriptionTier.BASIC
            )
        
        # Simulate payment to wrong destination
        wrong_destination = "rWrongDestinationAddress123"
        amount = 10.0
        tx_hash = mock_client.simulate_payment(
            from_account=test_sender_wallet,
            to_account=wrong_destination,
            amount=amount,
            memo=payment_info.memo
        )
        
        # Act
        with patch('app.xrpl_payments.XRPLClient', return_value=mock_client):
            verification_result = verify_payment(tx_hash)
        
        # Assert
        assert verification_result.verified is False
        assert "destination" in verification_result.reason.lower()

    @patch('app.xrpl_payments.XRPLClient')
    def test_verify_expired_payment(self, mock_xrpl_class, test_user, test_destination_wallet, test_sender_wallet):
        """Test verifying an expired payment request."""
        # Arrange
        mock_client = MockXRPLClient()
        mock_xrpl_class.return_value = mock_client
        
        # Create a payment request that's already expired
        with patch('app.xrpl_payments.XRPLClient', return_value=mock_client):
            with patch('app.xrpl_payments.datetime') as mock_datetime:
                # Set current time
                now = datetime.now()
                mock_datetime.now.return_value = now
                
                # Create payment request
                payment_info = create_payment_request(
                    user_id=test_user["id"],
                    tier=SubscriptionTier.BASIC
                )
                
                # Fast forward time beyond expiration
                future_time = now + timedelta(hours=2)  # Assuming 1 hour expiry
                mock_datetime.now.return_value = future_time
        
        # Simulate payment after expiration
        amount = 10.0
        tx_hash = mock_client.simulate_payment(
            from_account=test_sender_wallet,
            to_account=test_destination_wallet,
            amount=amount,
            memo=payment_info.memo
        )
        
        # Act
        with patch('app.xrpl_payments.XRPLClient', return_value=mock_client):
            with patch('app.xrpl_payments.datetime') as mock_datetime:
                mock_datetime.now.return_value = future_time
                verification_result = verify_payment(tx_hash)
        
        # Assert
        assert verification_result.verified is False
        assert "expired" in verification_result.reason.lower()

    @patch('app.xrpl_payments.XRPLClient')
    def test_get_payment_status_by_id(self, mock_xrpl_class, test_user, test_destination_wallet, test_sender_wallet):
        """Test retrieving payment status by ID."""
        # Arrange
        mock_client = MockXRPLClient()
        mock_xrpl_class.return_value = mock_client
        
        # Create a payment request
        with patch('app.xrpl_payments.XRPLClient', return_value=mock_client):
            payment_info = create_payment_request(
                user_id=test_user["id"],
                tier=SubscriptionTier.BASIC
            )
        
        payment_id = payment_info.payment_id
        
        # Act - Get status before payment
        with patch('app.xrpl_payments.XRPLClient', return_value=mock_client):
            status_before = get_payment_status(payment_id=payment_id)
        
        # Simulate the payment
        amount = 10.0
        tx_hash = mock_client.simulate_payment(
            from_account=test_sender_wallet,
            to_account=test_destination_wallet,
            amount=amount,
            memo=payment_info.memo
        )
        
        # Mock the database record of the payment verification
        with patch('app.xrpl_payments.XRPLClient', return_value=mock_client):
            verify_payment(tx_hash)
        
        # Act - Get status after payment
        with patch('app.xrpl_payments.XRPLClient', return_value=mock_client):
            status_after = get_payment_status(payment_id=payment_id)
        
        # Assert
        assert status_before.status == "pending"
        assert status_after.status == "completed"
        assert status_after.transaction_hash == tx_hash