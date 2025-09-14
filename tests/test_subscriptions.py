"""
Tests for subscription management.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from app.subscriptions import (
    SubscriptionTier, 
    TierDetails,
    Subscription,
    get_subscription_for_user,
    create_subscription,
    update_subscription,
    is_subscription_active,
    get_tier_details
)


@pytest.fixture
def test_user():
    """Fixture to provide a test user."""
    return {
        "id": "test_user_id",
        "email": "test@example.com",
        "username": "testuser",
    }


class TestSubscriptions:
    """Tests for subscription functionality."""
    
    def test_tier_details(self):
        """Test tier details are correctly initialized."""
        # Arrange & Act
        basic_tier = get_tier_details(SubscriptionTier.BASIC)
        premium_tier = get_tier_details(SubscriptionTier.PREMIUM)
        enterprise_tier = get_tier_details(SubscriptionTier.ENTERPRISE)
        
        # Assert
        assert basic_tier.name == SubscriptionTier.BASIC
        assert premium_tier.name == SubscriptionTier.PREMIUM
        assert enterprise_tier.name == SubscriptionTier.ENTERPRISE
        
        assert basic_tier.price_xrp < premium_tier.price_xrp
        assert premium_tier.price_xrp < enterprise_tier.price_xrp
        
        # Check feature count increases with tier level
        assert len(basic_tier.features) < len(premium_tier.features)
        assert len(premium_tier.features) < len(enterprise_tier.features)
    
    @patch('app.subscriptions.db')
    def test_create_subscription(self, mock_db, test_user):
        """Test creating a new subscription."""
        # Arrange
        user_id = test_user["id"]
        tier = SubscriptionTier.PREMIUM
        transaction_hash = "test_tx_hash"
        
        # Mock the database insert operation
        mock_db.insert_subscription.return_value = "sub_123"
        
        # Act
        subscription = create_subscription(
            user_id=user_id,
            tier=tier,
            transaction_hash=transaction_hash,
            amount_xrp=25.0
        )
        
        # Assert
        assert subscription.user_id == user_id
        assert subscription.tier == tier
        assert subscription.transaction_hash == transaction_hash
        assert subscription.status == "active"
        assert subscription.start_date <= datetime.now()
        assert subscription.end_date > datetime.now()
        
        # Verify database was called
        mock_db.insert_subscription.assert_called_once()
    
    @patch('app.subscriptions.db')
    def test_get_subscription_for_user_active(self, mock_db, test_user):
        """Test getting an active subscription for a user."""
        # Arrange
        user_id = test_user["id"]
        now = datetime.now()
        
        # Create a mock subscription that's active
        mock_subscription = {
            "id": "sub_123",
            "user_id": user_id,
            "tier": SubscriptionTier.PREMIUM,
            "start_date": now - timedelta(days=5),
            "end_date": now + timedelta(days=25),
            "status": "active",
            "transaction_hash": "test_tx_hash",
            "amount_xrp": 25.0
        }
        
        # Mock the database query
        mock_db.get_user_subscription.return_value = mock_subscription
        
        # Act
        subscription = get_subscription_for_user(user_id)
        
        # Assert
        assert subscription is not None
        assert subscription.id == mock_subscription["id"]
        assert subscription.tier == mock_subscription["tier"]
        assert subscription.status == "active"
        assert subscription.is_active() is True
    
    @patch('app.subscriptions.db')
    def test_get_subscription_for_user_expired(self, mock_db, test_user):
        """Test getting an expired subscription for a user."""
        # Arrange
        user_id = test_user["id"]
        now = datetime.now()
        
        # Create a mock subscription that's expired
        mock_subscription = {
            "id": "sub_123",
            "user_id": user_id,
            "tier": SubscriptionTier.BASIC,
            "start_date": now - timedelta(days=35),
            "end_date": now - timedelta(days=5),
            "status": "expired",
            "transaction_hash": "test_tx_hash",
            "amount_xrp": 10.0
        }
        
        # Mock the database query
        mock_db.get_user_subscription.return_value = mock_subscription
        
        # Act
        subscription = get_subscription_for_user(user_id)
        
        # Assert
        assert subscription is not None
        assert subscription.status == "expired"
        assert subscription.is_active() is False
    
    @patch('app.subscriptions.db')
    def test_get_subscription_for_user_none(self, mock_db, test_user):
        """Test getting a subscription when user has none."""
        # Arrange
        user_id = test_user["id"]
        
        # Mock the database query to return None
        mock_db.get_user_subscription.return_value = None
        
        # Act
        subscription = get_subscription_for_user(user_id)
        
        # Assert
        assert subscription is None
    
    @patch('app.subscriptions.db')
    def test_update_subscription(self, mock_db):
        """Test updating a subscription."""
        # Arrange
        subscription_id = "sub_123"
        new_end_date = datetime.now() + timedelta(days=60)
        
        # Mock the database update operation
        mock_db.update_subscription.return_value = True
        
        # Act
        result = update_subscription(
            subscription_id=subscription_id,
            status="extended",
            end_date=new_end_date
        )
        
        # Assert
        assert result is True
        mock_db.update_subscription.assert_called_once_with(
            subscription_id=subscription_id,
            status="extended",
            end_date=new_end_date
        )
    
    @patch('app.subscriptions.get_subscription_for_user')
    def test_is_subscription_active_true(self, mock_get_subscription, test_user):
        """Test checking if a subscription is active when it is."""
        # Arrange
        user_id = test_user["id"]
        
        # Create a mock active subscription
        mock_subscription = MagicMock()
        mock_subscription.is_active.return_value = True
        
        # Set up the mock to return our active subscription
        mock_get_subscription.return_value = mock_subscription
        
        # Act
        is_active = is_subscription_active(user_id)
        
        # Assert
        assert is_active is True
        mock_get_subscription.assert_called_once_with(user_id)
    
    @patch('app.subscriptions.get_subscription_for_user')
    def test_is_subscription_active_false(self, mock_get_subscription, test_user):
        """Test checking if a subscription is active when it's not."""
        # Arrange
        user_id = test_user["id"]
        
        # Create a mock inactive subscription
        mock_subscription = MagicMock()
        mock_subscription.is_active.return_value = False
        
        # Set up the mock to return our inactive subscription
        mock_get_subscription.return_value = mock_subscription
        
        # Act
        is_active = is_subscription_active(user_id)
        
        # Assert
        assert is_active is False
        mock_get_subscription.assert_called_once_with(user_id)
    
    @patch('app.subscriptions.get_subscription_for_user')
    def test_is_subscription_active_none(self, mock_get_subscription, test_user):
        """Test checking if a subscription is active when user has none."""
        # Arrange
        user_id = test_user["id"]
        
        # Set up the mock to return None (no subscription)
        mock_get_subscription.return_value = None
        
        # Act
        is_active = is_subscription_active(user_id)
        
        # Assert
        assert is_active is False
        mock_get_subscription.assert_called_once_with(user_id)