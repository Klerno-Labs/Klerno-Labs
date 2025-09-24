#
from __future__ import annotations

# Dummy db for test patching
db = None
# Utility for test compatibility

from datetime import UTC, datetime, timedelta


def is_subscription_active(user_id: str) -> bool:
    """Return True if the user's subscription is active, False otherwise."""

    sub = get_subscription_for_user(user_id)
    return bool(
        sub is not None
        and getattr(sub, "active", False)
        and getattr(sub, "expires_at", None)
        and sub.expires_at > datetime.now(UTC)
    )


def get_subscription_for_user(user_id: str) -> Subscription | None:
    """Alias for get_user_subscription for test compatibility."""
    return get_user_subscription(user_id)


"""
Subscriptions Module for Klerno Labs.

Manages user subscriptions, tier pricing, and access control.
"""

import sqlite3
from enum import Enum
from pathlib import Path
from typing import Any

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel

from .config import settings
from .security_session import get_current_user


class SubscriptionTier(str, Enum):
    """Subscription tier levels."""

    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class TierDetails(BaseModel):
    """Details for a subscription tier."""

    id: str
    name: str
    description: str
    price_xrp: float
    duration_days: int
    features: list[str]
    transaction_limit: int | None = None  # None=unlimited
    api_rate_limit: int | None = None  # requests per hour


class Subscription(BaseModel):
    """Subscription model."""

    id: str
    user_id: str
    tier: SubscriptionTier
    active: bool
    starts_at: datetime
    expires_at: datetime
    tx_hash: str | None = None
    payment_id: str | None = None
    auto_renew: bool = False
    created_at: datetime
    updated_at: datetime


# Default tier configuration - Aligned with advertised pricing
DEFAULT_TIERS = {
    SubscriptionTier.STARTER: TierDetails(
        id=SubscriptionTier.STARTER,
        name="Starter",
        description="Perfect for individual developers starting their journey",
        price_xrp=0.0,  # Free tier
        duration_days=30,
        transaction_limit=1000,  # 1, 000 transactions / month
        api_rate_limit=100,  # 100 requests / hour
        features=[
            "Up to 1, 000 transactions / month",
            "Starter risk analysis",
            "Email alerts",
            "Community support",
            "API access",
        ],
    ),
    SubscriptionTier.PROFESSIONAL: TierDetails(
        id=SubscriptionTier.PROFESSIONAL,
        name="Professional",
        description="Ideal for power users and small businesses",
        price_xrp=25.0,  # $99 / month worth in XRP (25 XRP * $4 / XRP=~$100)
        duration_days=30,
        transaction_limit=100000,  # 100, 000 transactions / month
        api_rate_limit=1000,  # 1, 000 requests / hour
        features=[
            "Up to 100, 000 transactions / month",
            "Advanced AI risk scoring",
            "Real - time WebSocket alerts",
            "Priority support",
            "Custom dashboards",
            "Compliance reporting",
            "Multi - chain support",
        ],
    ),
    SubscriptionTier.ENTERPRISE: TierDetails(
        id=SubscriptionTier.ENTERPRISE,
        name="Enterprise",
        description="Complete solution for businesses with advanced needs",
        price_xrp=0.0,  # Custom pricing - contact sales
        duration_days=30,
        transaction_limit=None,  # Unlimited transactions
        api_rate_limit=None,  # Unlimited API access
        features=[
            "Unlimited transactions",
            "White - label solution",
            "Dedicated support",
            "Custom integrations",
            "SLA guarantees",
            "On - premise deployment",
            "Custom AI models",
        ],
    ),
}


# In - memory cache for tier configuration
_tier_cache: dict[str, TierDetails] = {}


def init_subscription_db():
    """Initialize the subscription database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create subscription table
    cursor.execute(
        """
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
    """
    )

    # Create tiers table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS subscription_tiers (
        id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            price_xrp REAL NOT NULL,
            duration_days INTEGER NOT NULL,
            features TEXT NOT NULL
    )
    """
    )

    # Insert default tiers if not exist
    for _tier_id, tier in DEFAULT_TIERS.items():
        cursor.execute(
            """
            INSERT OR IGNORE INTO subscription_tiers
            (id, name, description, price_xrp, duration_days, features)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                tier.id,
                tier.name,
                tier.description,
                tier.price_xrp,
                tier.duration_days,
                ",".join(tier.features),
            ),
        )

    conn.commit()
    conn.close()


def get_db_connection():
    """Get a database connection."""
    if settings.USE_SQLITE:
        # Ensure directory exists using pathlib
        Path(settings.SQLITE_PATH).resolve().parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(settings.SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    else:
        # Use PostgreSQL instead (not implemented in this example)
        # In a real application, you'd use SQLAlchemy or another ORM
        raise NotImplementedError("PostgreSQL support not implemented")


# import typing helpers at module top; duplicate removed


def get_tier_details(tier_id: str | SubscriptionTier) -> TierDetails:
    """Get details for a subscription tier."""
    # Coerce incoming identifier to a SubscriptionTier when possible so we
    # can index DEFAULT_TIERS (which uses SubscriptionTier enum keys).
    tier_key: SubscriptionTier
    if isinstance(tier_id, SubscriptionTier):
        tier_key = tier_id
    else:
        try:
            tier_key = SubscriptionTier(tier_id)
        except Exception:
            # If coercion fails, leave as-is to trigger fallback later
            tier_key = tier_id  # type: ignore[assignment]

    # Check cache first
    if tier_key in _tier_cache:
        return _tier_cache[tier_key]

    # Query database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        (
            "SELECT id, name, description, price_xrp, duration_days, features "
            "FROM subscription_tiers WHERE id=?"
        ),
        (tier_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        # Fallback to default
        if tier_key in DEFAULT_TIERS:
            _tier_cache[tier_key] = DEFAULT_TIERS[tier_key]
            return DEFAULT_TIERS[tier_key]
        raise ValueError(f"Subscription tier {tier_id} not found")

    tier = TierDetails(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        price_xrp=row["price_xrp"],
        duration_days=row["duration_days"],
        features=row["features"].split(","),
    )

    # Cache for future use
    _tier_cache[tier_key] = tier

    return tier


def get_all_tiers() -> list[TierDetails]:
    """Get all subscription tiers."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, description, price_xrp, duration_days, features "
        "FROM subscription_tiers"
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
            features=row["features"].split(","),
        )
        # Update cache
        _tier_cache[tier.id] = tier
        tiers.append(tier)

    return tiers


def get_user_subscription(user_id: str) -> Subscription | None:
    """Get the current subscription for a user."""
    # If a db facade is provided (e.g., in tests), delegate to it
    if db is not None and hasattr(db, "get_user_subscription"):
        ret = db.get_user_subscription(user_id)
        if ret is None:
            return None
        # If already a Subscription instance, return as - is
        if isinstance(ret, Subscription):
            return ret
        # If dict - like, construct Subscription
        try:
            data = dict(ret)
        except Exception:
            # Assume attribute - style access
            data = ret.__dict__

        def _parse_dt(val: str) -> datetime:
            d = datetime.fromisoformat(val)
            if d.tzinfo is None:
                d = d.replace(tzinfo=UTC)
            return d

        tier_val = (
            data["tier"]
            if isinstance(data["tier"], SubscriptionTier)
            else SubscriptionTier(data["tier"])
        )
        starts_at = data.get("starts_at", datetime.now(UTC))
        if isinstance(starts_at, str):
            starts_at = _parse_dt(starts_at)
        expires_at = data.get("expires_at", datetime.now(UTC))
        if isinstance(expires_at, str):
            expires_at = _parse_dt(expires_at)
        created_at = data.get("created_at", datetime.now(UTC))
        if isinstance(created_at, str):
            created_at = _parse_dt(created_at)
        updated_at = data.get("updated_at", datetime.now(UTC))
        if isinstance(updated_at, str):
            updated_at = _parse_dt(updated_at)

        return Subscription(
            id=data["id"],
            user_id=data["user_id"],
            tier=tier_val,
            active=bool(data["active"]),
            starts_at=starts_at,
            expires_at=expires_at,
            tx_hash=data.get("tx_hash"),
            payment_id=data.get("payment_id"),
            auto_renew=bool(data.get("auto_renew", False)),
            created_at=created_at,
            updated_at=updated_at,
        )

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, user_id, tier, active, starts_at, expires_at, tx_hash, payment_id,
               auto_renew, created_at, updated_at
        FROM subscriptions
        WHERE user_id=?
        ORDER BY expires_at DESC
        LIMIT 1
        """,
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    def _parse_dt_db(val: str) -> datetime:
        d = datetime.fromisoformat(val)
        if d.tzinfo is None:
            d = d.replace(tzinfo=UTC)
        return d

    return Subscription(
        id=row["id"],
        user_id=row["user_id"],
        tier=SubscriptionTier(row["tier"]),
        active=bool(row["active"]),
        starts_at=_parse_dt_db(row["starts_at"]),
        expires_at=_parse_dt_db(row["expires_at"]),
        tx_hash=row["tx_hash"],
        payment_id=row["payment_id"],
        auto_renew=bool(row["auto_renew"]),
        created_at=_parse_dt_db(row["created_at"]),
        updated_at=_parse_dt_db(row["updated_at"]),
    )


def create_subscription(
    user_id: str,
    tier: SubscriptionTier,
    tx_hash: str | None = None,
    payment_id: str | None = None,
    duration_days: int | None = None,
    auto_renew: bool = False,
) -> Subscription:
    """Create a new subscription for a user."""
    import uuid

    # Get tier details to determine duration if not specified
    tier_details = get_tier_details(tier)
    days = duration_days if duration_days is not None else tier_details.duration_days

    now = datetime.now(UTC)

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
        updated_at=now,
    )

    # Use db facade if available (tests)
    if db is not None and hasattr(db, "insert_subscription"):
        # If existing and we are extending, prefer update_subscription when available
        if existing and existing.id == sub_id and hasattr(db, "update_subscription"):
            db.update_subscription(subscription)
        else:
            db.insert_subscription(subscription)
        return subscription

    conn = get_db_connection()
    cursor = conn.cursor()

    if existing and existing.id == sub_id:
        # Update existing subscription
        cursor.execute(
            """
            UPDATE subscriptions
            SET tier=?, active=?, expires_at=?, tx_hash=?,
                payment_id=?, auto_renew=?, updated_at=?
            WHERE id=?
            """,
            (
                subscription.tier,
                int(subscription.active),
                subscription.expires_at.isoformat(),
                subscription.tx_hash,
                subscription.payment_id,
                int(subscription.auto_renew),
                subscription.updated_at.isoformat(),
                subscription.id,
            ),
        )
    else:
        # Insert new subscription
        cursor.execute(
            """
            INSERT INTO subscriptions
            (id, user_id, tier, active, starts_at, expires_at, tx_hash, payment_id,
             auto_renew, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
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
                subscription.updated_at.isoformat(),
            ),
        )

    conn.commit()
    conn.close()

    return subscription


def update_subscription(subscription: Subscription) -> Subscription:
    """Update an existing subscription."""
    # Use db facade if available (tests)
    if db is not None and hasattr(db, "update_subscription"):
        db.update_subscription(subscription)
        return subscription

    conn = get_db_connection()
    cursor = conn.cursor()

    subscription.updated_at = datetime.now(UTC)

    cursor.execute(
        """
        UPDATE subscriptions
        SET tier=?, active=?, starts_at=?, expires_at=?, tx_hash=?,
            payment_id=?, auto_renew=?, updated_at=?
        WHERE id=?
        """,
        (
            subscription.tier,
            int(subscription.active),
            subscription.starts_at.isoformat(),
            subscription.expires_at.isoformat(),
            subscription.tx_hash,
            subscription.payment_id,
            int(subscription.auto_renew),
            subscription.updated_at.isoformat(),
            subscription.id,
        ),
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
    subscription = get_user_subscription(user_id)
    if not subscription:
        return False

    # Check if subscription is active and not expired
    return subscription.active and subscription.expires_at > datetime.now(UTC)


def get_all_subscriptions(limit: int = 100, offset: int = 0) -> list[Subscription]:
    """Get all subscriptions (for admin purposes)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, user_id, tier, active, starts_at, expires_at, tx_hash, payment_id,
               auto_renew, created_at, updated_at
        FROM subscriptions
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        (limit, offset),
    )
    rows = cursor.fetchall()
    conn.close()

    def _parse_dt_db(val: str) -> datetime:
        d = datetime.fromisoformat(val)
        if d.tzinfo is None:
            d = d.replace(tzinfo=UTC)
        return d

    return [
        Subscription(
            id=row["id"],
            user_id=row["user_id"],
            tier=SubscriptionTier(row["tier"]),
            active=bool(row["active"]),
            starts_at=_parse_dt_db(row["starts_at"]),
            expires_at=_parse_dt_db(row["expires_at"]),
            tx_hash=row["tx_hash"],
            payment_id=row["payment_id"],
            auto_renew=bool(row["auto_renew"]),
            created_at=_parse_dt_db(row["created_at"]),
            updated_at=_parse_dt_db(row["updated_at"]),
        )
        for row in rows
    ]


# FastAPI dependency for requiring an active subscription


async def require_active_subscription(
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """FastAPI dependency that requires an active subscription."""
    # Admin users always have access
    if current_user.get("role") == "admin":
        return current_user

    # Check for active subscription
    if not has_active_subscription(current_user["id"]):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Active subscription required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return current_user


def check_transaction_limit(user_id: str) -> tuple[bool, int, int]:
    """
    Check if user has exceeded transaction limit.
    Returns: (allowed, used_count, limit)
    """
    subscription = get_user_subscription(user_id)
    if not subscription:
        # No subscription = starter tier limits
        tier_details = DEFAULT_TIERS[SubscriptionTier.STARTER]
    else:
        tier_details = get_tier_details(subscription.tier.value)

    # If unlimited, always allow
    if tier_details.transaction_limit is None:
        return True, 0, -1  # -1 indicates unlimited

    # Count transactions for current billing period
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create usage table if not exists
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS transaction_usage (
        user_id TEXT NOT NULL,
            transaction_date DATE NOT NULL,
            count INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, transaction_date)
    )
    """
    )

    # Get current month usage
    from datetime import date

    current_month = date.today().replace(day=1)

    cursor.execute(
        """
        SELECT COALESCE(SUM(count), 0) FROM transaction_usage
        WHERE user_id=? AND transaction_date >= ?
        """,
        (user_id, current_month.isoformat()),
    )

    used_count = cursor.fetchone()[0]
    conn.close()

    return (
        used_count < tier_details.transaction_limit,
        used_count,
        tier_details.transaction_limit,
    )


def record_transaction_usage(user_id: str, count: int = 1):
    """Record transaction usage for billing."""
    conn = get_db_connection()
    cursor = conn.cursor()

    from datetime import date

    today = date.today().isoformat()

    cursor.execute(
        (
            """
            INSERT OR REPLACE INTO transaction_usage (user_id, transaction_date, count)
            VALUES (
                ?, ?, COALESCE(
                    (
                        SELECT count FROM transaction_usage
                        WHERE user_id=? AND transaction_date=?
                    ),
                        0
                ) + ?
            )
            """
        ),
        (user_id, today, user_id, today, count),
    )

    conn.commit()
    conn.close()


# In the shim we intentionally do not initialize DB on import to avoid
# filesystem/database side-effects during test-time imports. The real
# implementation initializes the DB when the application starts.
