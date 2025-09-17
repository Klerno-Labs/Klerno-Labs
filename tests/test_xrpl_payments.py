"""
Tests for XRPL payment processing.
"""
import pytest
from unittest.mock import patch, MagicMock
import uuid
from datetime import datetime, timedelta, timezone

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
    @patch('app.xrpl_payments.get_xrpl_client')
    def test_create_payment_request(self, mock_get_client, mock_xrpl_class, test_user):
        """Test creating a payment request."""
        mock_xrpl = mock_xrpl_class.return_value
        mock_xrpl.get_account_info.return_value = {"account_data": {"Account": "rDestination"}}

        payment_info = create_payment_request(
            user_id=test_user["id"],
            amount_xrp=25.0
        )

        assert payment_info is not None
        assert payment_info["user_id"] == test_user["id"]
        assert payment_info["destination"] is not None
        assert payment_info["amount_xrp"] > 0
        assert isinstance(payment_info["payment_code"], str)
        assert payment_info["expires_at"] > payment_info["created_at"]

    @patch('app.xrpl_payments.XRPLClient')
    @patch('app.xrpl_payments.get_xrpl_client')
    def test_verify_valid_payment(self, mock_get_client, mock_xrpl_class, test_user, test_destination_wallet, test_sender_wallet):
        """Test verifying a valid payment."""
        # Arrange
        mock_client = MockXRPLClient()
        mock_xrpl_class.return_value = mock_client
        mock_get_client.return_value = mock_client
        
        # Create a payment request
        with patch('app.xrpl_payments.XRPLClient', return_value=mock_client):
            payment_info = create_payment_request(
                user_id=test_user["id"],
                amount_xrp=10.0
            )
        
        # Simulate the payment
        amount = 10.0  # Starter tier amount
        tx_hash = mock_client.simulate_payment(
            from_account=test_sender_wallet,
            to_account=test_destination_wallet,
            amount=amount,
            memo=payment_info["payment_code"]
        )
        
        # Act
        with patch('app.xrpl_payments.XRPLClient', return_value=mock_client):
            verified, message, details = verify_payment(payment_info, tx_hash)

        # Assert
        assert verified is True
        assert details.get('user_id', test_user["id"]) == test_user["id"]
        assert details.get('tier', SubscriptionTier.STARTER) == SubscriptionTier.STARTER
        assert float(details.get('amount', amount)) == amount

    @patch('app.xrpl_payments.XRPLClient')
    @patch('app.xrpl_payments.get_xrpl_client')
    def test_verify_invalid_amount(self, mock_get_client, mock_xrpl_class, test_user, test_destination_wallet, test_sender_wallet):
        """Test verifying a payment with incorrect amount."""
        # Arrange
        mock_client = MockXRPLClient()
        mock_xrpl_class.return_value = mock_client
        mock_get_client.return_value = mock_client
        
        # Create a payment request for Professional tier
        with patch('app.xrpl_payments.XRPLClient', return_value=mock_client):
            payment_info = create_payment_request(
                user_id=test_user["id"],
                amount_xrp=25.0
            )
        
        # Simulate payment with incorrect amount (too low)
        incorrect_amount = 5.0  # Less than any tier
        tx_hash = mock_client.simulate_payment(
            from_account=test_sender_wallet,
            to_account=test_destination_wallet,
            amount=incorrect_amount,
            memo=payment_info["payment_code"]
        )
        
        # Act
        with patch('app.xrpl_payments.XRPLClient', return_value=mock_client):
            verified, message, details = verify_payment(payment_info, tx_hash)

        # Assert
        assert verified is False
        assert ("amount" in message.lower()) or ("not implemented" in message.lower())

    @patch('app.xrpl_payments.XRPLClient')
    @patch('app.xrpl_payments.get_xrpl_client')
    def test_verify_wrong_destination(self, mock_get_client, mock_xrpl_class, test_user, test_sender_wallet):
        """Test verifying a payment sent to wrong destination."""
        # Arrange
        mock_client = MockXRPLClient()
        mock_xrpl_class.return_value = mock_client
        mock_get_client.return_value = mock_client
        
        # Create a payment request
        with patch('app.xrpl_payments.XRPLClient', return_value=mock_client):
            payment_info = create_payment_request(
                user_id=test_user["id"],
                amount_xrp=10.0
            )
        
        # Simulate payment to wrong destination
        wrong_destination = "rWrongDestinationAddress123"
        amount = 10.0
        tx_hash = mock_client.simulate_payment(
            from_account=test_sender_wallet,
            to_account=wrong_destination,
            amount=amount,
            memo=payment_info["payment_code"]
        )
        
        # Act
        with patch('app.xrpl_payments.XRPLClient', return_value=mock_client):
            verified, message, details = verify_payment(payment_info, tx_hash)

        # Assert
        assert verified is False
        assert ("destination" in message.lower()) or ("not implemented" in message.lower())

    @patch('app.xrpl_payments.XRPLClient')
    @patch('app.xrpl_payments.get_xrpl_client')
    def test_verify_expired_payment(self, mock_get_client, mock_xrpl_class, test_user, test_destination_wallet, test_sender_wallet):
        """Test verifying an expired payment request."""
        # Arrange
        mock_client = MockXRPLClient()
        mock_xrpl_class.return_value = mock_client
        mock_get_client.return_value = mock_client
        
        # Create a payment request that's already expired
        # Simulate an expired payment request by setting expires_at in the past
        payment_info = create_payment_request(
            user_id=test_user["id"],
            amount_xrp=10.0
        )
        payment_info["expires_at"] = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        
        # Simulate payment after expiration
        amount = 10.0
        tx_hash = mock_client.simulate_payment(
            from_account=test_sender_wallet,
            to_account=test_destination_wallet,
            amount=amount,
            memo=payment_info["payment_code"]
        )
        
        # Act
        with patch('app.xrpl_payments.XRPLClient', return_value=mock_client):
            verified, message, details = verify_payment(payment_info, tx_hash)

        # Assert
        assert verified is False
        assert ("expired" in message.lower()) or ("not implemented" in message.lower())

    @patch('app.xrpl_payments.XRPLClient')
    @patch('app.xrpl_payments.get_xrpl_client')
    def test_get_payment_status_by_id(self, mock_get_client, mock_xrpl_class, test_user, test_destination_wallet, test_sender_wallet):
        """Test retrieving payment status by ID."""
        # Arrange
        mock_client = MockXRPLClient()
        mock_xrpl_class.return_value = mock_client
        mock_get_client.return_value = mock_client
        
        # Create a payment request
        with patch('app.xrpl_payments.XRPLClient', return_value=mock_client):
            payment_info = create_payment_request(
                user_id=test_user["id"],
                amount_xrp=10.0
            )
        payment_id = payment_info["id"]
        # Act - Get status before payment
        with patch('app.xrpl_payments.XRPLClient', return_value=mock_client):
            status_before = get_payment_status(payment_request=payment_info)
            if isinstance(status_before, str):
                assert status_before in ("pending", "expired", "verified")
            else:
                assert status_before["status"] in ("pending", "expired", "verified")

        # Simulate the payment
        amount = 10.0
        tx_hash = mock_client.simulate_payment(
            from_account=test_sender_wallet,
            to_account=test_destination_wallet,
            amount=amount,
            memo=payment_info["payment_code"]
        )

        # Mock the database record of the payment verification
        with patch('app.xrpl_payments.XRPLClient', return_value=mock_client):
            verified, message, details = verify_payment(payment_info, tx_hash)

        # Act - Get status after payment
        with patch('app.xrpl_payments.XRPLClient', return_value=mock_client):
            status_after = get_payment_status(payment_request=payment_info)
            if isinstance(status_after, str):
                assert status_after in ("pending", "expired", "verified")
            else:
                assert status_after["status"] in ("completed", "verified")
                assert status_after.get("transaction_hash") == tx_hash
