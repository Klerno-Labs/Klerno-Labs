"""
Subscriptions Module for Klerno Labs.

Manages user subscriptions, tier pricing, and access control.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple, Union

import sqlite3
from fastapi import Depends, HTTPException, status
from pydantic import BaseModel, Field

from .config import settings
from .security_session import get_current_user


class SubscriptionTier(str, Enum):
    """Subscription tier levels."""
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class TierDetails(BaseModel):
    """Details for a subscription tier."""
    id: str
    name: str
    description: str
    price_xrp: float
    duration_days: int
    features: List[str]


class Subscription(BaseModel):
    """Subscription model."""
    id: str
    user_id: str
    tier: SubscriptionTier
    active: bool
    starts_at: datetime
    expires_at: datetime
    tx_hash: Optional[str] = None
    payment_id: Optional[str] = None
    auto_renew: bool = False
    created_at: datetime
    updated_at: datetime


# Default tier configuration
DEFAULT_TIERS = {
    SubscriptionTier.BASIC: TierDetails(
        id=SubscriptionTier.BASIC,
        name="Basic",
        description="Access to core XRPL analytics and transaction monitoring",
        price_xrp=10.0,
        duration_days=30,
        features=[
            "XRPL transaction monitoring", 
            "Basic risk scoring", 
            "Transaction history"
        ]
    ),
    SubscriptionTier.PREMIUM: TierDetails(
        id=SubscriptionTier.PREMIUM,
        name="Premium",
        description="Advanced analytics and real-time alerts",
        price_xrp=25.0,
        duration_days=30,
        features=[
            "All Basic features",
            "Advanced risk scoring",
            "Real-time alerts",
            "Customizable dashboards",
            "Priority support"
        ]
    ),
    SubscriptionTier.ENTERPRISE: TierDetails(
        id=SubscriptionTier.ENTERPRISE,
        name="Enterprise",
        description="Enterprise-grade XRPL intelligence with API access",
        price_xrp=100.0,
        duration_days=30,
        features=[
            "All Premium features",
            "API access",
            "Custom integrations",
            "Dedicated support",
            "Compliance reporting",
            "Multi-user access"
        ]
    )
}


# In-memory cache for tier configuration
_tier_cache: Dict[str, TierDetails] = {}


def init_subscription_db():
    """Initialize the subscription database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create subscription table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS subscriptions (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        tier TEXT NOT NULL,
        active INTEGER NOT NULL,
        starts_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        tx_hash TEXT,
        payment_id TEXT,
        auto_renew INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    ''')
    
    # Create tiers table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS subscription_tiers (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        price_xrp REAL NOT NULL,
        duration_days INTEGER NOT NULL,
        features TEXT NOT NULL
    )
    ''')
    
    # Insert default tiers if not exist
    for tier_id, tier in DEFAULT_TIERS.items():
        cursor.execute(
            '''
            INSERT OR IGNORE INTO subscription_tiers 
            (id, name, description, price_xrp, duration_days, features)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (
                tier.id,
                tier.name,
                tier.description,
                tier.price_xrp,
                tier.duration_days,
                ','.join(tier.features)
            )
        )
    
    conn.commit()
    conn.close()


def get_db_connection():
    """Get a database connection."""
    if settings.USE_SQLITE:
        # Ensure directory exists
        import os
        os.makedirs(os.path.dirname(settings.SQLITE_PATH), exist_ok=True)
        
        conn = sqlite3.connect(settings.SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    else:
        # Use PostgreSQL instead (not implemented in this example)
        # In a real application, you'd use SQLAlchemy or another ORM
        raise NotImplementedError("PostgreSQL support not implemented")


def get_tier_details(tier_id: str) -> TierDetails:
    """Get details for a subscription tier."""
    # Check cache first
    if tier_id in _tier_cache:
        return _tier_cache[tier_id]
    
    # Query database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, description, price_xrp, duration_days, features FROM subscription_tiers WHERE id = ?",
        (tier_id,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        # Fallback to default
        if tier_id in DEFAULT_TIERS:
            _tier_cache[tier_id] = DEFAULT_TIERS[tier_id]
            return DEFAULT_TIERS[tier_id]
        raise ValueError(f"Subscription tier {tier_id} not found")
    
    tier = TierDetails(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        price_xrp=row["price_xrp"],
        duration_days=row["duration_days"],
        features=row["features"].split(",")
    )
    
    # Cache for future use
    _tier_cache[tier_id] = tier
    
    return tier


def get_all_tiers() -> List[TierDetails]:
    """Get all subscription tiers."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, description, price_xrp, duration_days, features FROM subscription_tiers"
    )
    rows = cursor.fetchall()
    conn.close()
    
    tiers = []
    for row in rows:
        tier = TierDetails(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            price_xrp=row["price_xrp"],
            duration_days=row["duration_days"],
            features=row["features"].split(",")
        )
        # Update cache
        _tier_cache[tier.id] = tier
        tiers.append(tier)
    
    return tiers


def get_user_subscription(user_id: str) -> Optional[Subscription]:
    """Get the current subscription for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT id, user_id, tier, active, starts_at, expires_at, tx_hash, payment_id, 
               auto_renew, created_at, updated_at 
        FROM subscriptions 
        WHERE user_id = ? 
        ORDER BY expires_at DESC 
        LIMIT 1
        ''',
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    return Subscription(
        id=row["id"],
        user_id=row["user_id"],
        tier=SubscriptionTier(row["tier"]),
        active=bool(row["active"]),
        starts_at=datetime.fromisoformat(row["starts_at"]),
        expires_at=datetime.fromisoformat(row["expires_at"]),
        tx_hash=row["tx_hash"],
        payment_id=row["payment_id"],
        auto_renew=bool(row["auto_renew"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"])
    )


def create_subscription(
    user_id: str,
    tier: SubscriptionTier,
    tx_hash: Optional[str] = None,
    payment_id: Optional[str] = None,
    duration_days: Optional[int] = None,
    auto_renew: bool = False
) -> Subscription:
    """Create a new subscription for a user."""
    import uuid
    
    # Get tier details to determine duration if not specified
    tier_details = get_tier_details(tier)
    days = duration_days if duration_days is not None else tier_details.duration_days
    
    now = datetime.utcnow()
    
    # Check if user already has a subscription
    existing = get_user_subscription(user_id)
    
    # If existing subscription is active, extend it
    if existing and existing.active and existing.expires_at > now:
        new_expires = existing.expires_at + timedelta(days=days)
        sub_id = existing.id
    else:
        # Create a new subscription
        new_expires = now + timedelta(days=days)
        sub_id = str(uuid.uuid4())
    
    subscription = Subscription(
        id=sub_id,
        user_id=user_id,
        tier=tier,
        active=True,
        starts_at=now,
        expires_at=new_expires,
        tx_hash=tx_hash,
        payment_id=payment_id,
        auto_renew=auto_renew,
        created_at=now,
        updated_at=now
    )
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if existing and existing.id == sub_id:
        # Update existing subscription
        cursor.execute(
            '''
            UPDATE subscriptions 
            SET tier = ?, active = ?, expires_at = ?, tx_hash = ?, 
                payment_id = ?, auto_renew = ?, updated_at = ?
            WHERE id = ?
            ''',
            (
                subscription.tier,
                int(subscription.active),
                subscription.expires_at.isoformat(),
                subscription.tx_hash,
                subscription.payment_id,
                int(subscription.auto_renew),
                subscription.updated_at.isoformat(),
                subscription.id
            )
        )
    else:
        # Insert new subscription
        cursor.execute(
            '''
            INSERT INTO subscriptions 
            (id, user_id, tier, active, starts_at, expires_at, tx_hash, payment_id, 
             auto_renew, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                subscription.id,
                subscription.user_id,
                subscription.tier,
                int(subscription.active),
                subscription.starts_at.isoformat(),
                subscription.expires_at.isoformat(),
                subscription.tx_hash,
                subscription.payment_id,
                int(subscription.auto_renew),
                subscription.created_at.isoformat(),
                subscription.updated_at.isoformat()
            )
        )
    
    conn.commit()
    conn.close()
    
    return subscription


def update_subscription(subscription: Subscription) -> Subscription:
    """Update an existing subscription."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    subscription.updated_at = datetime.utcnow()
    
    cursor.execute(
        '''
        UPDATE subscriptions 
        SET tier = ?, active = ?, starts_at = ?, expires_at = ?, tx_hash = ?, 
            payment_id = ?, auto_renew = ?, updated_at = ?
        WHERE id = ?
        ''',
        (
            subscription.tier,
            int(subscription.active),
            subscription.starts_at.isoformat(),
            subscription.expires_at.isoformat(),
            subscription.tx_hash,
            subscription.payment_id,
            int(subscription.auto_renew),
            subscription.updated_at.isoformat(),
            subscription.id
        )
    )
    
    conn.commit()
    conn.close()
    
    return subscription


def cancel_subscription(user_id: str) -> bool:
    """Cancel a user's subscription."""
    subscription = get_user_subscription(user_id)
    if not subscription:
        return False
    
    subscription.active = False
    subscription.auto_renew = False
    update_subscription(subscription)
    
    return True


def has_active_subscription(user_id: str) -> bool:
    """Check if a user has an active subscription."""
    if settings.DEMO_MODE:
        return True
        
    subscription = get_user_subscription(user_id)
    if not subscription:
        return False
    
    # Check if subscription is active and not expired
    return subscription.active and subscription.expires_at > datetime.utcnow()


def get_all_subscriptions(limit: int = 100, offset: int = 0) -> List[Subscription]:
    """Get all subscriptions (for admin purposes)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT id, user_id, tier, active, starts_at, expires_at, tx_hash, payment_id, 
               auto_renew, created_at, updated_at 
        FROM subscriptions 
        ORDER BY created_at DESC 
        LIMIT ? OFFSET ?
        ''',
        (limit, offset)
    )
    rows = cursor.fetchall()
    conn.close()
    
    return [
        Subscription(
            id=row["id"],
            user_id=row["user_id"],
            tier=SubscriptionTier(row["tier"]),
            active=bool(row["active"]),
            starts_at=datetime.fromisoformat(row["starts_at"]),
            expires_at=datetime.fromisoformat(row["expires_at"]),
            tx_hash=row["tx_hash"],
            payment_id=row["payment_id"],
            auto_renew=bool(row["auto_renew"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"])
        )
        for row in rows
    ]


# FastAPI dependency for requiring an active subscription
async def require_active_subscription(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """FastAPI dependency that requires an active subscription."""
    # Admin users always have access
    if current_user.get("role") == "admin":
        return current_user
    
    # Demo mode gives everyone access
    if settings.DEMO_MODE:
        return current_user
    
    # Check for active subscription
    if not has_active_subscription(current_user["id"]):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Active subscription required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return current_user


# Initialize the database on module import
init_subscription_db()