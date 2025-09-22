# app / paywall.py
import os

from fastapi import APIRouter, Body, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

from .deps import require_user

# Use the application's shared templates instance (templates are in the
# project top-level `templates/` directory). Creating a Jinja2Templates
# pointing at `app/templates` caused TemplateNotFound for paywall templates.
from .main import templates
from .security import expected_api_key
from .settings import settings

# from .subscriptions import get_user_subscription  # not used here
from .xrpl_payments import create_payment_request, verify_payment

router = APIRouter()

PAYWALL_CODE = os.getenv("PAYWALL_CODE", "Labs2025").strip()


@router.get("/paywall", include_in_schema=False)
def paywall(request: Request):
    err = request.query_params.get("err")
    return templates.TemplateResponse(
        "paywall_professional.html",
        {"request": request, "error": bool(err)},
    )


@router.post("/paywall/verify", include_in_schema=False)
def paywall_verify(code: str = Form(...)):
    accepted = PAYWALL_CODE or (expected_api_key() or "").strip()
    if accepted and code.strip() == accepted:
        api_key = (expected_api_key() or "").strip()
        target = "/dashboard"
        if api_key:
            target = f"/dashboard?key={api_key}"
        resp = RedirectResponse(url=target, status_code=303)
        resp.set_cookie(
            "cw_paid",
            "1",
            max_age=60 * 60 * 24 * 30,
            httponly=True,
            samesite="lax",
        )
        return resp
    return RedirectResponse(url="/paywall?err=1", status_code=303)


@router.get("/logout", include_in_schema=False)
def logout():
    resp = RedirectResponse(url="/paywall", status_code=303)
    resp.delete_cookie("cw_paid")
    return resp


# XRP Payment Routes
@router.post("/api/paywall/xrp-payment", include_in_schema=False)
async def create_xrp_payment_request(
    request: Request,
    amount_xrp: float = Body(...),
    tier: int = Body(1),
    _user=Depends(require_user),
):
    """Create a payment request for XRPL."""
    try:
        payment = create_payment_request(
            amount=amount_xrp,
            recipient=settings.XRP_WALLET_ADDRESS,
            sender=_user.get("email", ""),
            memo=f"Klerno Labs Subscription - Tier {tier}",
        )

        return JSONResponse(
            content={
                "success": True,
                "request_id": payment["request_id"],
                "destination_address": payment.get(
                    "recipient", settings.XRP_WALLET_ADDRESS
                ),
                "destination_tag": payment.get("destination_tag", "12345"),
                "amount": amount_xrp,
                "tier": tier,
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Failed to create payment request: {str(e)}",
            },
        )


@router.post("/api/paywall/verify-xrp", include_in_schema=False)
async def verify_xrp_payment_request(
    payment_id: str = Body(...),
    tx_hash: str = Body(...),
    _user=Depends(require_user),
):
    """Verify an XRPL payment."""
    try:
        # For demo, we create a new payment request with the same ID
        # In production, you would retrieve it from your database
        payment_request = create_payment_request(
            user_id=_user["id"],
            amount_xrp=settings.SUB_PRICE_XRP,
            description="Klerno Labs Subscription",
        )
        payment_request["id"] = payment_id

        # Verify the payment
        verified, message, tx_details = verify_payment(
            payment_request, tx_hash
        )

        if verified:
            # Set the subscription cookie
            resp = JSONResponse(
                content={
                    "verified": True,
                    "message": message,
                    "transaction": tx_details,
                }
            )
            resp.set_cookie(
                "cw_paid",
                "1",
                max_age=60 * 60 * 24 * 30,
                httponly=True,
                samesite="lax",
            )
            return resp

        return JSONResponse(content={"verified": False, "message": message})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to verify payment: {str(e)}"},
        )


@router.post("/api/paywall/verify-payment", include_in_schema=False)
async def verify_payment_endpoint(
    request_id: str = Body(...),
    transaction_hash: str = Body(...),
    _user=Depends(require_user),
):
    """Verify a payment transaction."""
    try:
        # Verify the payment using the transaction hash
        result = verify_payment(request_id, transaction_hash)

        if result.get("verified"):
            # Activate subscription for user
            from . import store

            store.update_user_subscription(_user["id"], active=True)

            return JSONResponse(
                content={
                    "success": True,
                    "message": "Payment verified successfully",
                    "transaction": result.get("transaction", {}),
                }
            )
        else:
            return JSONResponse(
                content={
                    "success": False,
                    "error": result.get(
                        "error", "Payment verification failed"
                    ),
                }
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Verification error: {str(e)}",
            },
        )


# Backwards compatible PaywallManager used in unit tests
class PaywallManager:
    def __init__(self):
        pass

    def is_paid(self, user_id: int) -> bool:
        # In tests, assume unpaid unless explicitly mocked
        return False

    def activate_subscription(self, user_id: int):
        # No-op for tests
        return True

    # Compatibility helpers used by unit tests
    def validate_subscription(self, user_data: dict) -> bool:
        expires = user_data.get("subscription_expires")
        if not expires:
            return False
        from datetime import datetime

        return expires > datetime.utcnow()

    def calculate_trial_remaining(self, signup_date):
        from datetime import datetime

        TRIAL_DAYS = 30
        if not signup_date:
            return 0
        days_used = (datetime.utcnow() - signup_date).days
        remain = TRIAL_DAYS - days_used
        return max(0, remain)
