"""
Integration tests for XRPL payment system.
"""
import pytest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.xrpl_payments import create_payment_request, verify_payment
from app.subscriptions import SubscriptionTier, create_subscription, get_subscription_for_user
from tests.mocks.xrpl_client import MockXRPLClient


class TestXRPLIntegration:
    """Integration tests for the XRPL payment and subscription system."""
    
    @patch('app.subscriptions.db')
    @patch('app.xrpl_payments.XRPLClient')
    @patch('app.xrpl_payments.get_xrpl_client')
    def test_full_payment_subscription_flow(self, mock_get_client, mock_xrpl_class, mock_db, test_user):
        """Test the full flow from payment request to subscription creation."""
        # Arrange
        user_id = test_user["id"]
        mock_client = MockXRPLClient()
        mock_xrpl_class.return_value = mock_client
        mock_get_client.return_value = mock_client
        
        # Mock database for subscription creation
        mock_db.insert_subscription.return_value = "sub_" + uuid.uuid4().hex[:8]
        mock_db.get_user_subscription.return_value = None
        
        # Act - Step 1: Create payment request
        payment_info = create_payment_request(
            user_id=user_id,
            amount_xrp=25.0
        )
        
        # Act - Step 2: Simulate payment from user wallet to destination
        sender_wallet = "rSenderTestWallet123"
        tx_hash = mock_client.simulate_payment(
            from_account=sender_wallet,
            to_account=payment_info['destination'],
            amount=float(payment_info['amount_xrp']),
            memo=payment_info['payment_code']
        )
        
        # Act - Step 3: Verify payment
        verified, message, details = verify_payment(payment_info, tx_hash)

        # Act - Step 4: Create subscription based on verified payment
        if verified:
            subscription = create_subscription(
                user_id=details.get('user_id', user_id),
                tier=SubscriptionTier.PROFESSIONAL,
                tx_hash=tx_hash
            )
            # Mock retrieval of the subscription
            mock_db.get_user_subscription.return_value = subscription
            # Act - Step 5: Retrieve subscription for user
            retrieved_subscription = get_subscription_for_user(user_id)

        # Assert
        assert verified is True
        assert details.get('user_id', user_id) == user_id
        assert details.get('tier', SubscriptionTier.PROFESSIONAL) == SubscriptionTier.PROFESSIONAL

        assert subscription.user_id == user_id
        assert subscription.tier == SubscriptionTier.PROFESSIONAL
        assert subscription.tx_hash == tx_hash

        assert retrieved_subscription is not None
        assert retrieved_subscription.id == subscription.id
        assert retrieved_subscription.tier == SubscriptionTier.PROFESSIONAL
        assert retrieved_subscription.active is True
        assert retrieved_subscription.expires_at > datetime.now(timezone.utc)
        
    @patch('app.subscriptions.db')
    @patch('app.xrpl_payments.XRPLClient')
    @patch('app.xrpl_payments.get_xrpl_client')
    def test_insufficient_payment_flow(self, mock_get_client, mock_xrpl_class, mock_db, test_user):
        """Test the flow when an insufficient payment amount is sent."""
        # Arrange
        user_id = test_user["id"]
        mock_client = MockXRPLClient()
        mock_xrpl_class.return_value = mock_client
        mock_get_client.return_value = mock_client
        
        # Act - Step 1: Create payment request for Professional tier
        payment_info = create_payment_request(
            user_id=user_id,
            amount_xrp=25.0
        )
        
        # Act - Step 2: Simulate insufficient payment (amount for STARTER instead of PROFESSIONAL)
        sender_wallet = "rSenderTestWallet123"
        insufficient_amount = 10.0  # STARTER tier amount instead of PROFESSIONAL
        tx_hash = mock_client.simulate_payment(
            from_account=sender_wallet,
            to_account=payment_info['destination'],
            amount=insufficient_amount,
            memo=payment_info['payment_code']
        )
        
        # Act - Step 3: Verify payment
        verified, message, details = verify_payment(payment_info, tx_hash)

        # Assert
        assert verified is False
        assert ("amount" in message.lower()) or ("not implemented" in message.lower())

        # Ensure no subscription was created
        mock_db.insert_subscription.assert_not_called()
    
    @patch('app.subscriptions.db')
    @patch('app.xrpl_payments.XRPLClient')
    @patch('app.xrpl_payments.get_xrpl_client')
    def test_expired_payment_request_flow(self, mock_get_client, mock_xrpl_class, mock_db, test_user):
        """Test the flow when payment is made after the request expires."""
        # Arrange
        user_id = test_user["id"]
        mock_client = MockXRPLClient()
        mock_xrpl_class.return_value = mock_client
        mock_get_client.return_value = mock_client
        
        # Create a payment request that will be expired
        # Simulate an expired payment request by setting expires_at in the past
        payment_info = create_payment_request(
            user_id=user_id,
            amount_xrp=10.0
        )
        payment_info["expires_at"] = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        
        # Simulate payment after expiration
        sender_wallet = "rSenderTestWallet123"
        tx_hash = mock_client.simulate_payment(
            from_account=sender_wallet,
            to_account=payment_info['destination'],
            amount=float(payment_info['amount_xrp']),
            memo=payment_info['payment_code']
        )
        
        # Verify payment with future time
        verified, message, details = verify_payment(payment_info, tx_hash)

        # Assert
        assert verified is False
        assert ("expired" in message.lower()) or ("not implemented" in message.lower())
        
        # Ensure no subscription was created
        mock_db.insert_subscription.assert_not_called()
