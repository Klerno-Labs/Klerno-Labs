from fastapi import Depends, HTTPException, Request, status
from jwt import DecodeError, ExpiredSignatureError, InvalidTokenError

from . import store
from .security_session import decode_jwt
from .settings import get_settings

S = get_settings()


def _lookup_user_by_sub(sub: str) -> dict | None:
    """
    `sub` may be a numeric user id OR an email. Try both.
    """
    # 1) try numeric id
    try:
        uid = int(sub)
        user = store.get_user_by_id(uid)
        if user:
            return user
    except (TypeError, ValueError):
        pass

    # 2) fall back to email
    if isinstance(sub, str) and hasattr(store, "get_user_by_email"):
        user = store.get_user_by_email(sub.strip().lower())
        if user:
            return user

    return None


def current_user(request: Request) -> dict | None:
    """
    Reads JWT from cookie 'session' or Authorization: Bearer <jwt>.
    Returns a user dict or None.
    """
    token: str | None = request.cookies.get("session")

    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()

    if not token:
        return None

    try:
        payload = decode_jwt(token)  # dict with "sub"
        sub = payload.get("sub")
        if not sub:
            return None
        return _lookup_user_by_sub(str(sub))
    except (ExpiredSignatureError, InvalidTokenError, DecodeError):
        # invalid / expired token
        return None


def require_user(user: dict | None = Depends(current_user)) -> dict:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login required",
        )
    return user


def require_paid_or_admin(user: dict = Depends(require_user)) -> dict:
    # Admin check
    if user.get("role") == "admin":
        return user

    # Legacy check
    if user.get("subscription_active"):
        return user

    # XRPL subscription check
    from .subscriptions import get_user_subscription

    subscription = get_user_subscription(user["id"])
    if subscription and subscription.is_active:
        # Add subscription info to user dict
        user["xrpl_subscription"] = {
            "tier": subscription.tier.value,
            "expires_at": (
                subscription.expires_at.isoformat() if subscription.expires_at else None
            ),
        }
        return user

    raise HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail="Subscription required",
    )


def require_admin(user: dict = Depends(require_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin only",
        )
    return user
