"""
Main integration file for updating app.main.py to use the new XRPL payment and subscription modules.
This file can be used as a reference to update the main application file.
"""

# Add these imports to the top of app.main.py
from app.config import settings
from app.xrpl_payments import create_payment_request, verify_payment, get_network_info
from app.subscriptions import (
    SubscriptionTier, TierDetails, Subscription, get_tier_details,
    get_all_tiers, get_user_subscription, create_subscription,
    has_active_subscription, require_active_subscription
)

# Example routes to add to app.main.py

# ---- XRPL Payment Routes ----

@app.get("/xrpl/network-info")
def xrpl_network_info(_user=Depends(require_user)):
    """Get information about the XRPL network configuration."""
    return get_network_info()

@app.post("/xrpl/payment-request")
def create_xrpl_payment(amount_xrp: Optional[float] = None, _user=Depends(require_user)):
    """Create a payment request for XRPL."""
    payment = create_payment_request(
        user_id=_user["id"],
        amount_xrp=amount_xrp or settings.SUB_PRICE_XRP,
        description="Klerno Labs Subscription"
    )
    return payment

@app.post("/xrpl/verify-payment")
def verify_xrpl_payment(
    payment_id: str,
    tx_hash: Optional[str] = None,
    _user=Depends(require_user)
):
    """Verify an XRPL payment and activate subscription if valid."""
    # Get payment request (this would come from your database in a real app)
    # For demo, we create a new one with the same ID
    payment_request = create_payment_request(
        user_id=_user["id"],
        amount_xrp=settings.SUB_PRICE_XRP,
        description="Klerno Labs Subscription"
    )
    payment_request["id"] = payment_id
    
    # Verify the payment
    verified, message, tx_details = verify_payment(payment_request, tx_hash)
    
    if verified and tx_details:
        # Create or extend subscription
        subscription = create_subscription(
            user_id=_user["id"],
            tier=SubscriptionTier.BASIC,
            tx_hash=tx_details["tx_hash"],
            payment_id=payment_id
        )
        
        return {
            "verified": True,
            "message": message,
            "transaction": tx_details,
            "subscription": subscription.model_dump()
        }
    
    return {
        "verified": False,
        "message": message
    }

# ---- Subscription Routes ----

@app.get("/subscriptions/tiers")
def list_subscription_tiers():
    """Get all available subscription tiers."""
    return [tier.model_dump() for tier in get_all_tiers()]

@app.get("/subscriptions/my-subscription")
def get_my_subscription(_user=Depends(require_user)):
    """Get current user's subscription."""
    subscription = get_user_subscription(_user["id"])
    if not subscription:
        return {"active": False, "subscription": None}
    
    is_active = subscription.active and subscription.expires_at > datetime.utcnow()
    return {
        "active": is_active,
        "subscription": subscription.model_dump(),
        "expires_in_days": (subscription.expires_at - datetime.utcnow()).days if is_active else 0
    }

# ---- Paywall Modifications ----

@app.get("/paywall", include_in_schema=False)
def paywall_page(request: Request, _user=Depends(require_user)):
    """Show paywall page with subscription options."""
    subscription = get_user_subscription(_user["id"])
    is_active = subscription and subscription.active and subscription.expires_at > datetime.utcnow()
    
    tiers = get_all_tiers()
    
    resp = templates.TemplateResponse(
        "paywall.html", 
        {
            "request": request,
            "title": "Subscription Required",
            "user": _user,
            "subscription": subscription.model_dump() if subscription else None,
            "is_active": is_active,
            "tiers": [t.model_dump() for t in tiers],
            "xrpl_network": settings.XRPL_NET,
            "destination_wallet": settings.DESTINATION_WALLET
        }
    )
    issue_csrf_cookie(resp)
    return resp