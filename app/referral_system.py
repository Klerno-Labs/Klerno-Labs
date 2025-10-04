"""Klerno Labs Referral System
Handles referral tracking, rewards, and viral growth mechanics
"""

import hashlib
import secrets
from datetime import datetime
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session


class ReferralCode(BaseModel):
    """Referral code data model"""

    code: str
    user_id: str
    created_at: datetime
    expires_at: datetime | None = None
    max_uses: int | None = None
    current_uses: int = 0
    reward_amount: float = 500.0
    currency: str = "USD"
    active: bool = True


class ReferralEvent(BaseModel):
    """Referral event tracking"""

    event_id: str
    referrer_id: str
    referee_id: str
    referral_code: str
    event_type: str  # 'signup', 'upgrade', 'payment'
    timestamp: datetime
    metadata: dict = {}


class ReferralReward(BaseModel):
    """Referral reward tracking"""

    reward_id: str
    referrer_id: str
    referee_id: str
    amount: float
    currency: str = "USD"
    status: str = "pending"  # pending, paid, cancelled
    earned_at: datetime
    paid_at: datetime | None = None


class ReferralManager:
    """Handles all referral system operations"""

    def __init__(self, db: Session | None):
        # Accept an optional Session for test/demo usage where a DB may not
        # be available. Callers in production should pass a real Session.
        self.db = db

    def generate_referral_code(self, user_id: str, prefix: str = "KL") -> str:
        """Generate a unique referral code for a user"""
        # Create a deterministic but secure code
        secret = f"{user_id}-{secrets.token_hex(8)}"
        hash_obj = hashlib.sha256(secret.encode())
        code_suffix = hash_obj.hexdigest()[:8].upper()
        return f"{prefix}{code_suffix}"

    def create_referral_link(self, user_id: str, campaign: str = "general") -> str:
        """Create a full referral link for sharing"""
        code = self.generate_referral_code(user_id)
        base_url = "https://klernolabs.com"
        return f"{base_url}/signup?ref={code}&campaign={campaign}"

    def track_referral_signup(self, referral_code: str, new_user_id: str) -> bool:
        """Track when someone signs up via a referral link"""
        # In a real implementation, this would:
        # 1. Validate the referral code
        # 2. Create a referral event record
        # 3. Apply any signup bonuses
        # 4. Send notifications

        event = ReferralEvent(
            event_id=secrets.token_hex(16),
            referrer_id=self._get_user_by_code(referral_code),
            referee_id=new_user_id,
            referral_code=referral_code,
            event_type="signup",
            timestamp=datetime.utcnow(),
            metadata={
                "signup_ip": self._get_request_ip(),
                "user_agent": self._get_user_agent(),
            },
        )

        # Store event (would be in database)
        return self._store_referral_event(event)

    def track_referral_conversion(
        self, user_id: str, plan_type: str, amount: float,
    ) -> bool:
        """Track when a referred user converts to paid"""
        # Find referral event for this user
        referral_event = self._get_referral_event_by_user(user_id)
        if not referral_event:
            return False

        # Create reward for referrer
        reward = ReferralReward(
            reward_id=secrets.token_hex(16),
            referrer_id=referral_event.referrer_id,
            referee_id=user_id,
            amount=500.0,  # Standard referral reward
            earned_at=datetime.utcnow(),
        )

        # Process reward
        return self._process_referral_reward(reward)

    def get_user_referral_stats(self, user_id: str) -> dict[str, Any]:
        """Get referral statistics for a user"""
        return {
            "referral_code": self.generate_referral_code(user_id),
            "total_referrals": self._count_user_referrals(user_id),
            "successful_conversions": self._count_user_conversions(user_id),
            "total_earned": self._calculate_total_earnings(user_id),
            "pending_rewards": self._calculate_pending_rewards(user_id),
            "referral_link": self.create_referral_link(user_id),
        }

    def generate_social_share_content(
        self, user_id: str, platform: str,
    ) -> dict[str, Any]:
        """Generate platform - specific sharing content"""
        referral_link = self.create_referral_link(user_id, f"social_{platform}")

        templates: dict[str, dict[str, Any]] = {
            "twitter": {
                "text": (
                    "Just discovered @KlernoLabs - AI-powered crypto compliance "
                    "that actually makes sense! Get explainable risk insights in real - "
                    "time. Perfect for compliance teams who want speed AND clarity."
                ),
                "url": referral_link,
                "hashtags": ["crypto", "compliance", "AI", "fintech"],
            },
            "linkedin": {
                "title": "Game - changing crypto compliance tool",
                "summary": (
                    "Klerno Labs transforms crypto compliance with explainable AI. "
                    "Real - time risk insights your team can trust."
                ),
                "url": referral_link,
            },
            "email": {
                "subject": (
                    "Check out Klerno Labs - Game - changing crypto compliance tool"
                ),
                "body": self._generate_email_template(referral_link),
            },
        }

        # Ensure the returned value is a dict for static type checkers
        val = templates.get(platform)
        if val is not None:
            return val
        return templates["twitter"]

    # Helper methods (would integrate with actual database / infrastructure)

    def _get_user_by_code(self, code: str) -> str:
        """Get user ID by referral code"""
        # Mock implementation
        return "user_123"

    def _get_request_ip(self) -> str:
        """Get current request IP"""
        return "127.0.0.1"

    def _get_user_agent(self) -> str:
        """Get current user agent"""
        return "Mozilla / 5.0..."

    def _store_referral_event(self, event: ReferralEvent) -> bool:
        """Store referral event in database"""
        # Mock implementation - would use actual database
        return True

    def _get_referral_event_by_user(self, user_id: str) -> ReferralEvent | None:
        """Get referral event for a user"""
        # Mock implementation
        return None

    def _process_referral_reward(self, reward: ReferralReward) -> bool:
        """Process and store referral reward"""
        # Mock implementation - would integrate with payment system
        return True

    def _count_user_referrals(self, user_id: str) -> int:
        """Count total referrals for user"""
        return 0

    def _count_user_conversions(self, user_id: str) -> int:
        """Count successful conversions for user"""
        return 0

    def _calculate_total_earnings(self, user_id: str) -> float:
        """Calculate total earnings for user"""
        return 0.0

    def _calculate_pending_rewards(self, user_id: str) -> float:
        """Calculate pending rewards for user"""
        return 0.0

    def _generate_email_template(self, referral_link: str) -> str:
        """Generate email sharing template"""
        return (
            "Hi there!\n\n"
            "I wanted to share this incredible tool I just found - Klerno Labs.\n\n"
            "It's an AI - powered compliance platform that gives you explainable risk "
            "insights for crypto transactions in real - time. Finally, a compliance "
            "tool that doesn't feel like a black box!\n\n"
            "What makes it special:\n"
            "[OK] Real - time XRPL monitoring\n"
            "[OK] AI explanations you can actually understand\n"
            "[OK] Built for compliance teams who need speed AND accuracy\n\n"
            "They're offering a free trial, and honestly, if you're in compliance, "
            "this could be a game - changer.\n\n"
            f"Check it out: {referral_link}\n\n"
            "Let me know what you think!\n\n"
            "Best regards"
        )


# Viral Growth Analytics


class ViralAnalytics:
    """Track and analyze viral growth metrics"""

    def __init__(self, db: Session):
        self.db = db

    def calculate_viral_coefficient(self, period_days: int = 30) -> float:
        """Calculate viral coefficient for given period"""
        # Viral coefficient = (# of new users from referrals) / (# of existing users)
        # Would use actual data from database
        return 0.45  # Mock value

    def get_referral_funnel(self) -> dict[str, Any]:
        """Get referral conversion funnel metrics"""
        return {
            "link_clicks": 1250,
            "signups": 487,
            "activations": 312,
            "conversions": 89,
            "conversion_rate": 7.12,
        }

    def get_top_referrers(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get top performing referrers"""
        return [
            {
                "user_id": "user_123",
                "referrals": 15,
                "conversions": 8,
                "earnings": 4000,
            },
            {
                "user_id": "user_456",
                "referrals": 12,
                "conversions": 6,
                "earnings": 3000,
            },
            # ... more mock data
        ]

    def track_sharing_event(self, user_id: str, platform: str, content_type: str):
        """Track when users share content"""
        event = {
            "user_id": user_id,
            "platform": platform,
            "content_type": content_type,
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": secrets.token_hex(8),
        }
        # Would store in analytics database
        return event


# Integration with existing auth system


def integrate_referral_with_signup(signup_data: dict, referral_code: str | None = None):
    """Integrate referral tracking with user signup"""
    if referral_code:
        # Track the referral signup (defensive: only call when we have a user_id)
        new_user_id = signup_data.get("user_id")
        if new_user_id:
            referral_manager = ReferralManager(
                db=None,
            )  # Would pass actual DB session in production
            referral_manager.track_referral_signup(referral_code, str(new_user_id))

        # Apply signup bonus (25% discount)
        signup_data["discount_code"] = "REFERRAL25"
        signup_data["discount_percentage"] = 25

    return signup_data


# Example usage for testing
if __name__ == "__main__":
    # Demo the referral system
    manager = ReferralManager(db=None)

    # Generate referral link
    link = manager.create_referral_link("user_123")
    print(f"Referral link: {link}")

    # Get sharing content
    twitter_content = manager.generate_social_share_content("user_123", "twitter")
    print(f"Twitter content: {twitter_content}")

    # Get user stats
    stats = manager.get_user_referral_stats("user_123")
    print(f"User stats: {stats}")
