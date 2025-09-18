from fastapi import APIRouter, Response, Depends, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
import json
import os
from typing import Optional, List

from .security_modules.password_policy import policy
from .security_modules import mfa

from . import store
from .security_session import hash_pw, verify_pw, issue_jwt
from .deps import require_user
from .settings import get_settings, Settings

router=APIRouter(prefix="/auth", tags=["auth"])
templates=Jinja2Templates(directory="app / templates")

# Single source of truth for config
S: Settings=get_settings()

# ---------- Schemas ----------


class SignupReq(BaseModel):
    email: EmailStr
    password: str


class LoginReq(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None


class MFASetupResponse(BaseModel):
    secret: str
    qr_uri: str
    recovery_codes: List[str]


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
    totp_code: Optional[str] = None


class UserOut(BaseModel):
    email: EmailStr
    role: str
    subscription_active: bool


class AuthResponse(BaseModel):
    ok: bool
    user: UserOut

# ---------- Helpers ----------


def _set_session_cookie(res: Response, token: str) -> None:
    """Set the session cookie with sane defaults."""
    res.set_cookie(
        key="session",
            value=token,
            httponly=True,
            secure=(S.app_env != "dev"),  # HTTPS in staging / prod
        samesite="lax",  # use "none" if cross - site SPA
        max_age=60 * 60 * 24 * 7,  # 7 days
        path="/",
            )

# ---------- Routes ----------

# Template Routes
@router.get("/signup", response_class=HTMLResponse)


def signup_page(request: Request):
    """Serve the enhanced signup page."""
    # Ensure templates have access to url_path_for
    templates.env.globals["url_path_for"] = request.app.url_path_for

    # Create context without importing main to avoid circular dependency
    context={
        "request": request,
            "url_path_for": request.app.url_path_for,
            "app_name": "Klerno Labs",
            "current_year": 2025
    }
    return templates.TemplateResponse("signup_enhanced.html", context)

@router.get("/login", response_class=HTMLResponse)


def login_page(request: Request, error: Optional[str] = None):
    """Serve the enhanced login page."""
    # Ensure templates have access to url_path_for
    templates.env.globals["url_path_for"] = request.app.url_path_for

    # Create context without importing main to avoid circular dependency
    context={
        "request": request,
            "url_path_for": request.app.url_path_for,
            "app_name": "Klerno Labs",
            "current_year": 2025,
            "error": error
    }
    return templates.TemplateResponse("login_enhanced.html", context)

# API Routes
@router.post("/signup", response_model=AuthResponse, status_code=201)


def signup_api(payload: SignupReq, res: Response):
    """API endpoint for programmatic signup."""
    from .security_modules.password_policy import policy
    email=payload.email.lower().strip()

    if store.get_user_by_email(email):
        raise HTTPException(status_code=409, detail="User already exists")

    # Password policy enforcement
    errors=policy.validate(payload.password, username=email.split("@")[0], email=email)
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))
    if policy.config.check_breaches and policy.check_breached(payload.password):
        raise HTTPException(status_code=400, detail="Password found in known breach database. Choose a different password.")

    # bootstrap: first user or ENV admin becomes admin + active subscription
    role="viewer"
    sub_active=False
    if email == S.admin_email or store.users_count() == 0:
        role, sub_active="admin", True

    # Generate MFA secret for new users
    totp_secret=mfa.generate_totp_secret()
    encrypted_secret=mfa.encrypt_seed(totp_secret)

    # Generate recovery codes
    recovery_codes=[mfa.generate_totp_secret()[:8] for _ in range(10)]

    user=store.create_user(
        email=email,
            password_hash=policy.hash(payload.password),
            role=role,
            subscription_active=sub_active,
            totp_secret=encrypted_secret,
            mfa_enabled=False,  # User needs to complete setup
        mfa_type="totp",
            recovery_codes=recovery_codes,
            has_hardware_key=False
    )
    token=issue_jwt(user["id"], user["email"], user["role"])
    _set_session_cookie(res, token)

    return {"ok": True, "user": {"email": user["email"], "role": user["role"], "subscription_active": user["subscription_active"]}}

@router.get("/mfa / setup")


def mfa_setup(user=Depends(require_user)):
    """Get MFA setup information for current user."""
    user_data=store.get_user_by_id(user["id"])
    if not user_data or not user_data.get("totp_secret"):
        raise HTTPException(status_code=400, detail="No MFA secret found for user")

    secret=mfa.decrypt_seed(user_data["totp_secret"])
    qr_uri=mfa.get_totp_uri(user["email"], secret)

    return MFASetupResponse(
        secret=secret,
            qr_uri=qr_uri,
            recovery_codes=user_data.get("recovery_codes", [])
    )

@router.post("/mfa / enable")


def enable_mfa(totp_code: str = Form(...), user=Depends(require_user)):
    """Enable MFA after user provides valid TOTP code."""
    user_data=store.get_user_by_id(user["id"])
    if not user_data or not user_data.get("totp_secret"):
        raise HTTPException(status_code=400, detail="No MFA secret found for user")

    secret=mfa.decrypt_seed(user_data["totp_secret"])
    if not mfa.verify_totp(totp_code, secret):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")

    # Enable MFA for user
    store.update_user_mfa(user["id"], mfa_enabled=True)

    return {"ok": True, "message": "MFA enabled successfully"}

@router.post("/password - reset / request")


def request_password_reset(payload: PasswordResetRequest):
    """Initiate password reset process."""
    email=payload.email.lower().strip()
    user=store.get_user_by_email(email)

    # Always return success to prevent email enumeration
    if not user:
        return {"ok": True, "message": "If the email exists, a reset link has been sent"}

    # Generate secure reset token
    import secrets
    import time
    reset_token=secrets.token_urlsafe(32)
    expires_at=int(time.time()) + 3600  # 1 hour expiration

    # Store reset token (you may want to add a password_reset_tokens table)
    # For now, we'll use a simple in - memory approach
    if not hasattr(store, '_reset_tokens'):
        store._reset_tokens={}

    store._reset_tokens[reset_token] = {
        'user_id': user['id'],
            'email': email,
            'expires_at': expires_at
    }

    # In production, send email with reset link
    # For now, return token for testing (remove in production)
    return {
        "ok": True,
            "message": "If the email exists, a reset link has been sent",
            "reset_token": reset_token  # Remove this in production
    }

@router.post("/password - reset / confirm")


def confirm_password_reset(payload: PasswordResetConfirm):
    """Complete password reset with new password."""
    # Validate reset token
    if not hasattr(store, '_reset_tokens') or payload.token not in store._reset_tokens:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    token_data=store._reset_tokens[payload.token]

    # Check token expiration
    import time
    if time.time() > token_data['expires_at']:
        del store._reset_tokens[payload.token]
        raise HTTPException(status_code=400, detail="Reset token has expired")

    # Get user
    user=store.get_user_by_id(token_data['user_id'])
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    # Check MFA if enabled
    if user.get("mfa_enabled", False):
        if not payload.totp_code:
            raise HTTPException(status_code=422, detail="TOTP code required for password reset")

        if not user.get("totp_secret"):
            raise HTTPException(status_code=500, detail="MFA enabled but no secret found")

        secret=mfa.decrypt_seed(user["totp_secret"])
        if not mfa.verify_totp(payload.totp_code, secret):
            raise HTTPException(status_code=401, detail="Invalid TOTP code")

    # Validate new password against policy
    email=user['email']
    errors=policy.validate(payload.new_password, username=email.split("@")[0], email=email)
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    if policy.config.check_breaches and policy.check_breached(payload.new_password):
        raise HTTPException(status_code=400, detail="Password found in known breach database. Choose a different password.")

    # Update password
    new_password_hash=policy.hash(payload.new_password)
    store.update_user_password(user['id'], new_password_hash)

    # Invalidate reset token
    del store._reset_tokens[payload.token]

    return {"ok": True, "message": "Password reset successfully"}

@router.post("/signup")


def signup_form(
    request: Request,
        email: str=Form(...),
        password: str=Form(...),
        wallet_addresses_json: Optional[str] = Form(None)
):
    """Handle form - based signup with wallet addresses."""
    try:
        email=email.lower().strip()
        if store.get_user_by_email(email):
            return templates.TemplateResponse(
                "signup_enhanced.html",
                    {"request": request, "error": "Email already registered. Please sign in instead."}
            )
        # Parse wallet addresses if provided
        wallet_addresses=[]
        if wallet_addresses_json:
            try:
                wallet_addresses=json.loads(wallet_addresses_json)
            except Exception:
                pass
        # Password policy enforcement
        errors=policy.validate(password, username=email.split("@")[0], email=email)
        if errors:
            return templates.TemplateResponse(
                "signup_enhanced.html",
                    {"request": request, "error": "; ".join(errors)}
            )
        if policy.config.check_breaches and policy.check_breached(password):
            return templates.TemplateResponse(
                "signup_enhanced.html",
                    {"request": request, "error": "Password found in known breach database. Choose a different password."}
            )
        # bootstrap: first user or ENV admin becomes admin + active subscription
        role="viewer"
        sub_active=False
        if email == S.admin_email or store.users_count() == 0:
            role, sub_active="admin", True

        # Generate MFA secret for new users
        totp_secret=mfa.generate_totp_secret()
        encrypted_secret=mfa.encrypt_seed(totp_secret)

        # Generate recovery codes
        recovery_codes=[mfa.generate_totp_secret()[:8] for _ in range(10)]

        user=store.create_user(
            email=email,
                password_hash=policy.hash(password),
                role=role,
                subscription_active=sub_active,
                wallet_addresses=wallet_addresses,
                totp_secret=encrypted_secret,
                mfa_enabled=False,  # User needs to complete setup
            mfa_type="totp",
                recovery_codes=recovery_codes,
                has_hardware_key=False
        )
        # Set session and redirect to dashboard
        token=issue_jwt(user["id"], user["email"], user["role"])
        response=RedirectResponse(url="/dashboard", status_code=302)
        _set_session_cookie(response, token)
        return response
    except Exception as e:
        return templates.TemplateResponse(
            "signup_enhanced.html",
                {"request": request, "error": f"Signup failed: {str(e)}"}
        )

@router.post("/login", response_model=AuthResponse)


def login_api(payload: LoginReq, res: Response):
    """API endpoint for programmatic login."""
    from .security_modules.password_policy import policy
    email=payload.email.lower().strip()
    user=store.get_user_by_email(email)

    if not user or not policy.verify(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Check if MFA is enabled for user
    if user.get("mfa_enabled", False):
        if not payload.totp_code:
            raise HTTPException(status_code=422, detail="TOTP code required")

        if not user.get("totp_secret"):
            raise HTTPException(status_code=500, detail="MFA enabled but no secret found")

        secret=mfa.decrypt_seed(user["totp_secret"])
        if not mfa.verify_totp(payload.totp_code, secret):
            raise HTTPException(status_code=401, detail="Invalid TOTP code")

    token=issue_jwt(user["id"], user["email"], user["role"])
    _set_session_cookie(res, token)

    return {"ok": True, "user": {"email": user["email"], "role": user["role"], "subscription_active": user["subscription_active"]}}

@router.post("/login")


def login_form(
    request: Request,
        email: str=Form(...),
        password: str=Form(...),
        totp_code: Optional[str] = Form(None)
):
    """Handle form - based login."""
    try:
        email=email.lower().strip()
        user=store.get_user_by_email(email)
        if not user or not policy.verify(password, user["password_hash"]):
            return templates.TemplateResponse(
                "login_enhanced.html",
                    {"request": request, "error": "Invalid email or password"}
            )

        # Check if MFA is enabled for user
        if user.get("mfa_enabled", False):
            if not totp_code:
                return templates.TemplateResponse(
                    "login_enhanced.html",
                        {"request": request, "error": "TOTP code required", "show_mfa": True}
                )

            if not user.get("totp_secret"):
                return templates.TemplateResponse(
                    "login_enhanced.html",
                        {"request": request, "error": "MFA configuration error"}
                )

            secret=mfa.decrypt_seed(user["totp_secret"])
            if not mfa.verify_totp(totp_code, secret):
                return templates.TemplateResponse(
                    "login_enhanced.html",
                        {"request": request, "error": "Invalid TOTP code", "show_mfa": True}
                )

        # Set session and redirect based on user role
        token=issue_jwt(user["id"], user["email"], user["role"])
        # Redirect admin users to admin panel, others to dashboard
        if user.get("role") == "admin":
            redirect_url="/admin"
        else:
            redirect_url="/dashboard"
        response=RedirectResponse(url=redirect_url, status_code=302)
        _set_session_cookie(response, token)
        return response
    except Exception as e:
        return templates.TemplateResponse(
            "login_enhanced.html",
                {"request": request, "error": f"Login failed: {str(e)}"}
        )

@router.post("/logout", status_code=204)


def logout(res: Response, user=Depends(require_user)):
    res.delete_cookie("session", path="/")
    # 204 No Content
    return Response(status_code=204)

@router.get("/me", response_model=UserOut)


def me(user=Depends(require_user)):
    return {"email": user["email"], "role": user["role"], "subscription_active": user["subscription_active"]}

# ---- DEV helpers while Stripe isn't live ----
@router.post("/mock / activate")


def mock_activate(user=Depends(require_user)):
    """Simulate a paid subscription for the current user."""
    if user["role"] == "admin":
        store.set_subscription_active(user["email"], True)
        return {"ok": True, "activated": True}
    raise HTTPException(status_code=403, detail="Only admin can mock")
