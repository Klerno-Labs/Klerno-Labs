# app / auth_enhanced.py
"""
Enhanced authentication system with role - based access control
supporting Owner, Admin, Manager, and User roles.
"""

from fastapi import APIRouter, Response, Depends, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
from typing import Optional
import jwt
from datetime import datetime, timedelta

from .models import User, UserRole, AccountStatus
from .admin_manager import AdminManager
from .security_session import hash_pw as get_password_hash, verify_pw as verify_password
from .settings import get_settings

router=APIRouter(prefix="/auth", tags=["auth"])
templates=Jinja2Templates(directory="app / templates")
settings=get_settings()
admin_manager=AdminManager()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SignupRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    success: bool
    message: str
    user: Optional[dict] = None
    token: Optional[str] = None


def create_access_token(user: User) -> str:
    """Create JWT access token for authenticated user."""
    payload={
        "user_id": user.id,
            "email": user.email,
            "role": user.role.value,
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow()
    }

    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def verify_access_token(token: str) -> Optional[User]:
    """Verify JWT token and return user if valid."""
    try:
        payload=jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        email=payload.get("email")

        if email:
            return admin_manager.get_user_by_email(email)
        return None
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


async def get_current_user(request: Request) -> Optional[User]:
    """Get current authenticated user from request."""
    # Try session cookie first
    token=request.cookies.get("session")

    # Try Authorization header if no cookie
    if not token:
        auth_header=request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token=auth_header[7:]

    if token:
        user=verify_access_token(token)
        if user and not user.is_blocked():
            # Update last login
            import sqlite3
            with sqlite3.connect(admin_manager.db_path) as conn:
                cursor=conn.cursor()
                cursor.execute("""
                    UPDATE users_enhanced SET last_login=? WHERE email=?
                """, (datetime.utcnow().isoformat(), user.email))
                conn.commit()

            return user

    return None


async def require_user(request: Request) -> User:
    """Require authenticated user or raise 401."""
    user=await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def require_admin(request: Request) -> User:
    """Require admin or higher access."""
    user=await require_user(request)
    if not user.is_admin_or_higher():
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def require_owner(request: Request) -> User:
    """Require owner access."""
    user=await require_user(request)
    if not user.is_owner():
        raise HTTPException(status_code=403, detail="Owner access required")
    return user


def set_session_cookie(response: Response, token: str):
    """Set secure session cookie."""
    response.set_cookie(
        key="session",
            value=token,
            httponly=True,
            secure=settings.app_env != "dev",
            samesite="lax",
            max_age=60 * 60 * 24,  # 24 hours
        path="/"
    )

@router.get("/login", response_class=HTMLResponse)


async def login_page(request: Request, error: Optional[str] = None):
    """Display login page."""
    return templates.TemplateResponse("login.html", {
        "request": request,
            "error": error
    })

@router.post("/login")


async def login(
    request: Request,
        email: str=Form(...),
        password: str=Form(...)
):
    """Handle login form submission."""
    try:
        email=email.lower().strip()
        user=admin_manager.get_user_by_email(email)

        if not user:
            return RedirectResponse(
                url="/auth / login?error=Invalid email or password",
                    status_code=302
            )

        # Check if user is blocked
        if user.is_blocked():
            return RedirectResponse(
                url="/auth / login?error=Account is blocked",
                    status_code=302
            )

        # Verify password
        if not verify_password(password, user.password_hash):
            # Log failed login attempt
            admin_manager.log_admin_action(
                admin_email="system",
                    target_email=email,
                    action="failed_login",
                    reason="Invalid password"
            )

            return RedirectResponse(
                url="/auth / login?error=Invalid email or password",
                    status_code=302
            )

        # Create token and set cookie
        token=create_access_token(user)

        # Determine redirect based on role
        if user.is_manager_or_higher():
            redirect_url="/admin / dashboard"
        elif user.is_premium:
            redirect_url="/dashboard"
        else:
            redirect_url="/dashboard"  # Free users get limited dashboard

        response=RedirectResponse(url=redirect_url, status_code=302)
        set_session_cookie(response, token)

        return response

    except Exception as e:
        return RedirectResponse(
            url="/auth / login?error=Login error occurred",
                status_code=302
        )

@router.post("/api / login")


async def api_login(login_data: LoginRequest) -> AuthResponse:
    """API endpoint for programmatic login."""
    try:
        email=login_data.email.lower().strip()
        user=admin_manager.get_user_by_email(email)

        if not user or not verify_password(login_data.password, user.password_hash):
            return AuthResponse(
                success=False,
                    message="Invalid email or password"
            )

        if user.is_blocked():
            return AuthResponse(
                success=False,
                    message="Account is blocked"
            )

        token=create_access_token(user)

        return AuthResponse(
            success=True,
                message="Login successful",
                user={
                "email": user.email,
                    "role": user.role.value,
                    "status": user.status.value,
                    "is_premium": user.is_premium
            },
                token=token
        )

    except Exception as e:
        return AuthResponse(
            success=False,
                message="Login error occurred"
        )

@router.get("/signup", response_class=HTMLResponse)


async def signup_page(request: Request):
    """Display signup page."""
    return templates.TemplateResponse("signup.html", {"request": request})

@router.post("/signup")


async def signup(
    request: Request,
        email: str=Form(...),
        password: str=Form(...)
):
    """Handle signup form submission."""
    try:
        email=email.lower().strip()

        # Check if user already exists
        if admin_manager.get_user_by_email(email):
            return RedirectResponse(
                url="/auth / signup?error=User already exists",
                    status_code=302
            )

        # Create user account (default role: USER)
        result=admin_manager.create_user(
            email=email,
                password=password,
                role=UserRole.USER,
                is_premium=False
        )

        if not result["success"]:
            return RedirectResponse(
                url=f"/auth / signup?error={result['message']}",
                    status_code=302
            )

        # Auto - login the new user
        user=admin_manager.get_user_by_email(email)
        token=create_access_token(user)

        response=RedirectResponse(url="/dashboard", status_code=302)
        set_session_cookie(response, token)

        return response

    except Exception as e:
        return RedirectResponse(
            url="/auth / signup?error=Signup error occurred",
                status_code=302
        )

@router.post("/api / signup")


async def api_signup(signup_data: SignupRequest) -> AuthResponse:
    """API endpoint for programmatic signup."""
    try:
        email=signup_data.email.lower().strip()

        if admin_manager.get_user_by_email(email):
            return AuthResponse(
                success=False,
                    message="User already exists"
            )

        result=admin_manager.create_user(
            email=email,
                password=signup_data.password,
                role=UserRole.USER,
                is_premium=False
        )

        if not result["success"]:
            return AuthResponse(
                success=False,
                    message=result["message"]
            )

        user=admin_manager.get_user_by_email(email)
        token=create_access_token(user)

        return AuthResponse(
            success=True,
                message="Account created successfully",
                user={
                "email": user.email,
                    "role": user.role.value,
                    "status": user.status.value,
                    "is_premium": user.is_premium
            },
                token=token
        )

    except Exception as e:
        return AuthResponse(
            success=False,
                message="Signup error occurred"
        )

@router.post("/logout")


async def logout(request: Request):
    """Handle logout."""
    response=RedirectResponse(url="/auth / login", status_code=302)
    response.delete_cookie("session", path="/")
    return response

@router.get("/me")


async def get_current_user_info(user: User = Depends(require_user)):
    """Get current user information."""
    return {
        "email": user.email,
            "role": user.role.value,
            "status": user.status.value,
            "is_premium": user.is_premium,
            "created_at": user.created_at.isoformat(),
            "last_login": user.last_login.isoformat() if user.last_login else None
    }
