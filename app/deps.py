from fastapi import Depends, HTTPException, Request, status
from jwt import DecodeError, ExpiredSignatureError, InvalidTokenError

from . import store
from .security_session import decode_jwt
from .settings import get_settings
from .store import UserDict


# Lazy settings proxy so importing this module doesn't eagerly initialize
# the app settings at import time.
class _LazySettings:
    def __init__(self, factory) -> None:
        self._factory = factory
        self._obj = None

    def _ensure(self) -> None:
        if self._obj is None:
            self._obj = self._factory()

    def __getattr__(self, name):
        self._ensure()
        return getattr(self._obj, name)


S = _LazySettings(get_settings)


def _lookup_user_by_sub(sub: str) -> UserDict | dict | None:
    """`sub` may be a numeric user id OR an email. Try both."""
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


def current_user(request: Request) -> UserDict | dict | None:
    """Reads JWT from cookie 'session' or Authorization: Bearer <jwt>.
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


def require_user(
    user: UserDict | dict | None = Depends(current_user),
) -> UserDict | dict:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login required",
        )
    return user


def require_paid_or_admin(
    user: UserDict | dict | None = Depends(current_user),
) -> UserDict | dict:
    # If no user (anonymous), treat as payment required to match tests' expectations
    if not user:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Subscription required",
        )

    # Admin check
    if user.get("role") == "admin":
        return user

    # Legacy check
    if user.get("subscription_active"):
        return user

    # XRPL subscription check
    from .subscriptions import get_user_subscription

    subscription = get_user_subscription(user["id"])
    if subscription:
        # Subscription model uses attribute 'active' in this codebase
        is_active = getattr(subscription, "active", None)
        if is_active:
            # Add subscription info to a shallow copy to avoid modifying
            # the TypedDict in-place (TypedDicts are static view types).
            augmented = dict(user)
            augmented["xrpl_subscription"] = {
                "tier": subscription.tier.value,
                "expires_at": (
                    subscription.expires_at.isoformat()
                    if subscription.expires_at
                    else None
                ),
            }
            return augmented

    raise HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail="Subscription required",
    )


def require_admin(user: UserDict | dict = Depends(require_user)) -> UserDict | dict:
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin only",
        )
    return user
