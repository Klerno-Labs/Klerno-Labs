import os
from fastapi import APIRouter, Request, Form, Depends, HTTPException, Body
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from .security import expected_api_key
from .deps import require_user
from .subscriptions import get_user_subscription, SubscriptionTier
from .xrpl_payments import create_payment_request, verify_payment
from .settings import settings

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

PAYWALL_CODE = os.getenv("PAYWALL_CODE", "Labs2025").strip()


@router.get("/paywall", include_in_schema=False)
def paywall(request: Request):
    err = request.query_params.get("err")
    return templates.TemplateResponse("paywall.html", {"request": request, "error": bool(err)})


@router.post("/paywall/verify", include_in_schema=False)
def paywall_verify(code: str = Form(...)):
    accepted = PAYWALL_CODE or (expected_api_key() or "").strip()
    if accepted and code.strip() == accepted:
        api_key = (expected_api_key() or "").strip()
        target = "/dashboard"
        if api_key:
            target = f"/dashboard?key={api_key}"
        resp = RedirectResponse(url=target, status_code=303)
        resp.set_cookie("cw_paid", "1", max_age=60 * 60 * 24 * 30, httponly=True, samesite="lax")
        return resp
    return RedirectResponse(url="/paywall?err=1", status_code=303)


@router.get("/logout", include_in_schema=False)
def logout():
    resp = RedirectResponse(url="/paywall", status_code=303)
    resp.delete_cookie("cw_paid")
    return resp

# XRP Payment Routes
@router.post("/api/paywall/xrp-payment", include_in_schema=False)
async def create_xrp_payment_request(amount_xrp: float = Body(None), _user=Depends(require_user)):
    """Create a payment request for XRPL."""
    try:
        payment = create_payment_request(
            user_id=_user["id"],
            amount_xrp=amount_xrp or settings.SUB_PRICE_XRP,
            description="Klerno Labs Subscription"
        )
        return payment
    except Exception as e:
        return JSONResponse(
            status_code=500, 
            content={"error": f"Failed to create payment request: {str(e)}"}
        )

@router.post("/api/paywall/verify-xrp", include_in_schema=False)
async def verify_xrp_payment_request(
    payment_id: str = Body(...),
    tx_hash: str = Body(...),
    _user=Depends(require_user)
):
    """Verify an XRPL payment."""
    try:
        # For demo, we create a new payment request with the same ID
        # In production, you would retrieve it from your database
        payment_request = create_payment_request(
            user_id=_user["id"],
            amount_xrp=settings.SUB_PRICE_XRP,
            description="Klerno Labs Subscription"
        )
        payment_request["id"] = payment_id
        
        # Verify the payment
        verified, message, tx_details = verify_payment(payment_request, tx_hash)
        
        if verified:
            # Set the subscription cookie
            resp = JSONResponse(content={
                "verified": True,
                "message": message,
                "transaction": tx_details
            })
            resp.set_cookie("cw_paid", "1", max_age=60*60*24*30, httponly=True, samesite="lax")
            return resp
        
        return JSONResponse(content={
            "verified": False,
            "message": message
        })
    except Exception as e:
        return JSONResponse(
            status_code=500, 
            content={"error": f"Failed to verify payment: {str(e)}"}
        )
        return JSONResponse(
            status_code=500, 
            content={"error": f"Failed to create payment request: {str(e)}"}
        )

@router.post("/api/paywall/verify-xrp", include_in_schema=False)
async def verify_xrp_payment_request(
    payment_id: str = Body(...),
    tx_hash: str = Body(...),
    _user=Depends(require_user)
):
    """Verify an XRPL payment."""
    try:
        # For demo, we create a new payment request with the same ID
        # In production, you would retrieve it from your database
        payment_request = create_payment_request(
            user_id=_user["id"],
            amount_xrp=settings.SUB_PRICE_XRP,
            description="Klerno Labs Subscription"
        )
        payment_request["id"] = payment_id
        
        # Verify the payment
        verified, message, tx_details = verify_payment(payment_request, tx_hash)
        
        if verified:
            # Set the subscription cookie
            resp = JSONResponse(content={
                "verified": True,
                "message": message,
                "transaction": tx_details
            })
            resp.set_cookie("cw_paid", "1", max_age=60*60*24*30, httponly=True, samesite="lax")
            return resp
        
        return JSONResponse(content={
            "verified": False,
            "message": message
        })
    except Exception as e:
        return JSONResponse(
            status_code=500, 
            content={"error": f"Failed to verify payment: {str(e)}"}
        )
