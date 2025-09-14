"""
Integration tests for XRPL payment system.
"""
import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

from app.xrpl_payments import create_payment_request, verify_payment
from app.subscriptions import SubscriptionTier, create_subscription, get_subscription_for_user
from tests.mocks.xrpl_client import MockXRPLClient


class TestXRPLIntegration:
    """Integration tests for the XRPL payment and subscription system."""
    
    @patch('app.xrpl_payments.XRPLClient')
    @patch('app.subscriptions.db')
    def test_full_payment_subscription_flow(self, mock_db, mock_xrpl_class, test_user):
        """Test the full flow from payment request to subscription creation."""
        # Arrange
        user_id = test_user["id"]
        mock_client = MockXRPLClient()
        mock_xrpl_class.return_value = mock_client
        
        # Mock database for subscription creation
        mock_db.insert_subscription.return_value = "sub_" + uuid.uuid4().hex[:8]
        mock_db.get_user_subscription.return_value = None
        
        # Act - Step 1: Create payment request
        with patch('app.xrpl_payments.XRPLClient', return_value=mock_client):
            payment_info = create_payment_request(
                user_id=user_id,
                tier=SubscriptionTier.PREMIUM
            )
        
        # Act - Step 2: Simulate payment from user wallet to destination
        sender_wallet = "rSenderTestWallet123"
        tx_hash = mock_client.simulate_payment(
            from_account=sender_wallet,
            to_account=payment_info.destination_address,
            amount=float(payment_info.amount_xrp),
            memo=payment_info.memo
        )
        
        # Act - Step 3: Verify payment
        with patch('app.xrpl_payments.XRPLClient', return_value=mock_client):
            verification_result = verify_payment(tx_hash)
        
        # Act - Step 4: Create subscription based on verified payment
        if verification_result.verified:
            subscription = create_subscription(
                user_id=verification_result.user_id,
                tier=verification_result.tier,
                transaction_hash=tx_hash,
                amount_xrp=float(verification_result.amount)
            )
        
            # Mock retrieval of the subscription
            mock_db.get_user_subscription.return_value = {
                "id": subscription.id,
                "user_id": subscription.user_id,
                "tier": subscription.tier,
                "status": subscription.status,
                "start_date": subscription.start_date,
                "end_date": subscription.end_date,
                "transaction_hash": subscription.transaction_hash,
                "amount_xrp": subscription.amount_xrp
            }
            
            # Act - Step 5: Retrieve subscription for user
            retrieved_subscription = get_subscription_for_user(user_id)
        
        # Assert
        assert verification_result.verified is True
        assert verification_result.user_id == user_id
        assert verification_result.tier == SubscriptionTier.PREMIUM
        
        assert subscription.user_id == user_id
        assert subscription.tier == SubscriptionTier.PREMIUM
        assert subscription.transaction_hash == tx_hash
        assert subscription.status == "active"
        
        assert retrieved_subscription is not None
        assert retrieved_subscription.id == subscription.id
        assert retrieved_subscription.tier == SubscriptionTier.PREMIUM
        assert retrieved_subscription.is_active() is True
        
    @patch('app.xrpl_payments.XRPLClient')
    @patch('app.subscriptions.db')
    def test_insufficient_payment_flow(self, mock_db, mock_xrpl_class, test_user):
        """Test the flow when an insufficient payment amount is sent."""
        # Arrange
        user_id = test_user["id"]
        mock_client = MockXRPLClient()
        mock_xrpl_class.return_value = mock_client
        
        # Act - Step 1: Create payment request for Premium tier
        with patch('app.xrpl_payments.XRPLClient', return_value=mock_client):
            payment_info = create_payment_request(
                user_id=user_id,
                tier=SubscriptionTier.PREMIUM
            )
        
        # Act - Step 2: Simulate insufficient payment (amount for BASIC instead of PREMIUM)
        sender_wallet = "rSenderTestWallet123"
        insufficient_amount = 10.0  # Basic tier amount instead of Premium
        tx_hash = mock_client.simulate_payment(
            from_account=sender_wallet,
            to_account=payment_info.destination_address,
            amount=insufficient_amount,
            memo=payment_info.memo
        )
        
        # Act - Step 3: Verify payment
        with patch('app.xrpl_payments.XRPLClient', return_value=mock_client):
            verification_result = verify_payment(tx_hash)
        
        # Assert
        assert verification_result.verified is False
        assert "amount" in verification_result.reason.lower()
        
        # Ensure no subscription was created
        mock_db.insert_subscription.assert_not_called()
    
    @patch('app.xrpl_payments.XRPLClient')
    @patch('app.subscriptions.db')
    def test_expired_payment_request_flow(self, mock_db, mock_xrpl_class, test_user):
        """Test the flow when payment is made after the request expires."""
        # Arrange
        user_id = test_user["id"]
        mock_client = MockXRPLClient()
        mock_xrpl_class.return_value = mock_client
        
        # Create a payment request that will be expired
        with patch('app.xrpl_payments.XRPLClient', return_value=mock_client):
            with patch('app.xrpl_payments.datetime') as mock_datetime:
                # Set current time
                now = datetime(2025, 9, 14, 10, 0, 0)
                mock_datetime.now.return_value = now
                
                payment_info = create_payment_request(
                    user_id=user_id,
                    tier=SubscriptionTier.BASIC
                )
                
                # Fast forward time past expiration
                future_time = now + timedelta(hours=2)  # Assuming 1 hour expiration
                mock_datetime.now.return_value = future_time
        
        # Simulate payment after expiration
        sender_wallet = "rSenderTestWallet123"
        tx_hash = mock_client.simulate_payment(
            from_account=sender_wallet,
            to_account=payment_info.destination_address,
            amount=float(payment_info.amount_xrp),
            memo=payment_info.memo
        )
        
        # Verify payment with future time
        with patch('app.xrpl_payments.XRPLClient', return_value=mock_client):
            with patch('app.xrpl_payments.datetime') as mock_datetime:
                mock_datetime.now.return_value = future_time
                verification_result = verify_payment(tx_hash)
        
        # Assert
        assert verification_result.verified is False
        assert "expired" in verification_result.reason.lower()
        
        # Ensure no subscription was created
        mock_db.insert_subscription.assert_not_called()