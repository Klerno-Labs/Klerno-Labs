from fastapi import APIRouter, Response, Depends, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
import json
from typing import Optional, List

from . import store
from .security_session import hash_pw, verify_pw, issue_jwt
from .deps import require_user
from .settings import get_settings, Settings

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="app/templates")

# Single source of truth for config
S: Settings = get_settings()

# ---------- Schemas ----------
class SignupReq(BaseModel):
    email: EmailStr
    password: str

class LoginReq(BaseModel):
    email: EmailStr
    password: str

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
        secure=(S.app_env != "dev"),   # HTTPS in staging/prod
        samesite="lax",                # use "none" if cross-site SPA
        max_age=60 * 60 * 24 * 7,      # 7 days
        path="/",
    )

# ---------- Routes ----------

# Template Routes
@router.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    """Serve the enhanced signup page."""
    return templates.TemplateResponse("signup_enhanced.html", {"request": request})

@router.get("/login", response_class=HTMLResponse)  
def login_page(request: Request, error: Optional[str] = None):
    """Serve the enhanced login page."""
    return templates.TemplateResponse("login_enhanced.html", {"request": request, "error": error})

# API Routes
@router.post("/signup", response_model=AuthResponse, status_code=201)
def signup_api(payload: SignupReq, res: Response):
    """API endpoint for programmatic signup."""
    email = payload.email.lower().strip()

    if store.get_user_by_email(email):
        raise HTTPException(status_code=409, detail="User already exists")

    # bootstrap: first user or ENV admin becomes admin + active subscription
    role = "viewer"
    sub_active = False
    if email == S.admin_email or store.users_count() == 0:
        role, sub_active = "admin", True

    user = store.create_user(
        email=email,
        password_hash=hash_pw(payload.password),
        role=role,
        subscription_active=sub_active,
    )
    token = issue_jwt(user["id"], user["email"], user["role"])
    _set_session_cookie(res, token)

    return {"ok": True, "user": {"email": user["email"], "role": user["role"], "subscription_active": user["subscription_active"]}}

@router.post("/signup")
def signup_form(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    wallet_addresses_json: Optional[str] = Form(None)
):
    """Handle form-based signup with wallet addresses."""
    try:
        email = email.lower().strip()
        
        if store.get_user_by_email(email):
            return templates.TemplateResponse(
                "signup_enhanced.html", 
                {"request": request, "error": "Email already registered. Please sign in instead."}
            )

        # Parse wallet addresses if provided
        wallet_addresses = []
        if wallet_addresses_json:
            try:
                wallet_addresses = json.loads(wallet_addresses_json)
            except:
                pass
        
        # bootstrap: first user or ENV admin becomes admin + active subscription
        role = "viewer"
        sub_active = False
        if email == S.admin_email or store.users_count() == 0:
            role, sub_active = "admin", True

        user = store.create_user(
            email=email,
            password_hash=hash_pw(password),
            role=role,
            subscription_active=sub_active,
            wallet_addresses=wallet_addresses
        )
        
        # Set session and redirect to dashboard
        token = issue_jwt(user["id"], user["email"], user["role"])
        response = RedirectResponse(url="/dashboard", status_code=302)
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
    email = payload.email.lower().strip()
    user = store.get_user_by_email(email)

    if not user or not verify_pw(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = issue_jwt(user["id"], user["email"], user["role"])
    _set_session_cookie(res, token)

    return {"ok": True, "user": {"email": user["email"], "role": user["role"], "subscription_active": user["subscription_active"]}}

@router.post("/login")
def login_form(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    """Handle form-based login."""
    try:
        email = email.lower().strip()
        user = store.get_user_by_email(email)

        if not user or not verify_pw(password, user["password_hash"]):
            return templates.TemplateResponse(
                "login_enhanced.html", 
                {"request": request, "error": "Invalid email or password"}
            )

        # Set session and redirect based on user role
        token = issue_jwt(user["id"], user["email"], user["role"])
        
        # Redirect admin users to admin panel, others to dashboard
        if user.get("role") == "admin":
            redirect_url = "/admin"
        else:
            redirect_url = "/dashboard"
            
        response = RedirectResponse(url=redirect_url, status_code=302)
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
@router.post("/mock/activate")
def mock_activate(user=Depends(require_user)):
    """Simulate a paid subscription for the current user."""
    if user["role"] == "admin":
        store.set_subscription_active(user["email"], True)
        return {"ok": True, "activated": True}
    raise HTTPException(status_code=403, detail="Only admin can mock")
