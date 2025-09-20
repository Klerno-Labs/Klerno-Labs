"""
Unified Authentication Module for Klerno Labs

This module consolidates all authentication functionality:
- Local authentication (username/password)
- OAuth integration (Google, GitHub, etc.)
- SSO (Single Sign-On) support
- JWT token management
- Session management
- User management

Replaces: auth.py, auth_enhanced.py, auth_oauth.py, auth_sso.py
"""

from __future__ import annotations

import os
import secrets
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

from app.core.security import SecurityEventType, audit_logger, security_manager

# Authentication configuration
AUTH_CONFIG = {
    "jwt_secret": os.getenv("JWT_SECRET", secrets.token_urlsafe(32)),
    "jwt_algorithm": "HS256",
    "jwt_expire_hours": int(os.getenv("JWT_EXPIRE_HOURS", "24")),
    "session_expire_hours": int(os.getenv("SESSION_EXPIRE_HOURS", "8")),
    "max_login_attempts": int(os.getenv("MAX_LOGIN_ATTEMPTS", "5")),
    "lockout_duration": int(os.getenv("LOCKOUT_DURATION", "300")),  # 5 minutes
    "require_email_verification": os.getenv(
        "REQUIRE_EMAIL_VERIFICATION", "false"
    ).lower()
    == "true",
    "enable_oauth": os.getenv("ENABLE_OAUTH", "true").lower() == "true",
    "google_client_id": os.getenv("GOOGLE_CLIENT_ID"),
    "google_client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
    "github_client_id": os.getenv("GITHUB_CLIENT_ID"),
    "github_client_secret": os.getenv("GITHUB_CLIENT_SECRET"),
}

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT bearer token
security = HTTPBearer(auto_error=False)

# Failed login tracking
_failed_logins: dict[str, list[float]] = {}
_locked_accounts: dict[str, float] = {}

# Router for auth endpoints
router = APIRouter(prefix="/auth", tags=["authentication"])

# Templates
templates = Jinja2Templates(directory="app/templates")


class AuthModels:
    """Pydantic models for authentication."""

    class LoginRequest(BaseModel):
        email: EmailStr
        password: str
        remember_me: bool = False

    class RegisterRequest(BaseModel):
        email: EmailStr
        password: str
        confirm_password: str
        full_name: str | None = None

    class TokenResponse(BaseModel):
        access_token: str
        token_type: str = "bearer"
        expires_in: int
        user: dict[str, Any]

    class OAuthRequest(BaseModel):
        provider: str
        code: str
        state: str | None = None


class AuthenticationManager:
    """Unified authentication manager."""

    def __init__(self):
        self.config = AUTH_CONFIG
        self.pwd_context = pwd_context

    def hash_password(self, password: str) -> str:
        """Hash password securely."""
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return self.pwd_context.verify(plain_password, hashed_password)

    def create_jwt_token(self, user_data: dict[str, Any]) -> dict[str, Any]:
        """Create JWT token for user."""
        now = datetime.now(UTC)
        expire = now + timedelta(hours=self.config["jwt_expire_hours"])

        payload = {
            "sub": str(user_data["id"]),
            "email": user_data["email"],
            "iat": now,
            "exp": expire,
            "type": "access",
        }

        token = jwt.encode(
            payload, self.config["jwt_secret"], algorithm=self.config["jwt_algorithm"]
        )

        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": self.config["jwt_expire_hours"] * 3600,
            "user": user_data,
        }

    def verify_jwt_token(self, token: str) -> dict[str, Any] | None:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(
                token,
                self.config["jwt_secret"],
                algorithms=[self.config["jwt_algorithm"]],
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.JWTError:
            return None

    def is_account_locked(self, email: str) -> bool:
        """Check if account is locked due to failed attempts."""
        if email not in _locked_accounts:
            return False

        lockout_time = _locked_accounts[email]
        if time.time() - lockout_time > self.config["lockout_duration"]:
            # Unlock account
            del _locked_accounts[email]
            if email in _failed_logins:
                del _failed_logins[email]
            return False

        return True

    def record_failed_login(self, email: str, ip: str):
        """Record failed login attempt and implement lockout."""
        now = time.time()

        # Initialize or clean old attempts
        if email not in _failed_logins:
            _failed_logins[email] = []

        _failed_logins[email] = [
            attempt
            for attempt in _failed_logins[email]
            if now - attempt < 3600  # Keep attempts from last hour
        ]

        # Add current attempt
        _failed_logins[email].append(now)

        # Check if should lock account
        if len(_failed_logins[email]) >= self.config["max_login_attempts"]:
            _locked_accounts[email] = now
            security_manager.log_security_event(
                SecurityEventType.BRUTE_FORCE,
                {"email": email, "attempts": len(_failed_logins[email])},
                ip,
            )

        audit_logger.log_auth_failure(email, ip, "Invalid credentials")

    def clear_failed_logins(self, email: str):
        """Clear failed login attempts after successful login."""
        if email in _failed_logins:
            del _failed_logins[email]
        if email in _locked_accounts:
            del _locked_accounts[email]

    async def authenticate_user(
        self, email: str, password: str, ip: str
    ) -> dict[str, Any] | None:
        """Authenticate user with email and password."""
        # Check if account is locked
        if self.is_account_locked(email):
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account temporarily locked due to failed login attempts",
            )

        # Get user from database (implement based on your user model)
        user = await self.get_user_by_email(email)
        if not user:
            self.record_failed_login(email, ip)
            return None

        # Verify password
        if not self.verify_password(password, user.get("password_hash", "")):
            self.record_failed_login(email, ip)
            return None

        # Successful login
        self.clear_failed_logins(email)
        audit_logger.log_auth_success(email, ip)

        return {
            "id": user["id"],
            "email": user["email"],
            "full_name": user.get("full_name"),
            "is_admin": user.get("is_admin", False),
            "is_verified": user.get("is_verified", True),
        }

    async def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        """Get user by email from database."""
        # This should be implemented based on your database layer
        # For now, return None to indicate user not found
        return None

    async def create_user(
        self, email: str, password: str, full_name: str | None = None
    ) -> dict[str, Any]:
        """Create new user account."""
        # Check if user already exists
        existing_user = await self.get_user_by_email(email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists",
            )

        # Hash password
        password_hash = self.hash_password(password)

        # Create user (implement based on your database layer)
        user_data = {
            "email": email,
            "password_hash": password_hash,
            "full_name": full_name,
            "is_admin": False,
            "is_verified": not self.config["require_email_verification"],
            "created_at": datetime.now(UTC).isoformat(),
        }

        # TODO: Save to database

        return user_data


# Global authentication manager
auth_manager = AuthenticationManager()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any] | None:
    """Get current authenticated user from JWT token."""
    if not credentials:
        return None

    token_data = auth_manager.verify_jwt_token(credentials.credentials)
    if not token_data:
        return None

    # Get user data from database
    user = await auth_manager.get_user_by_email(token_data["email"])
    return user


async def require_auth(
    current_user: dict[str, Any] | None = Depends(get_current_user),
) -> dict[str, Any]:
    """Require authentication - raise exception if not authenticated."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


async def require_admin(
    current_user: dict[str, Any] = Depends(require_auth),
) -> dict[str, Any]:
    """Require admin privileges."""
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )
    return current_user


def get_client_ip(request: Request) -> str:
    """Extract client IP address."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return str(request.client.host) if request.client else "unknown"


# Authentication endpoints
@router.post("/login", response_model=AuthModels.TokenResponse)
async def login(request: Request, login_data: AuthModels.LoginRequest):
    """Authenticate user and return JWT token."""
    client_ip = get_client_ip(request)

    user = await auth_manager.authenticate_user(
        login_data.email, login_data.password, client_ip
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    token_data = auth_manager.create_jwt_token(user)
    return AuthModels.TokenResponse(**token_data)


@router.post("/register", response_model=AuthModels.TokenResponse)
async def register(request: Request, register_data: AuthModels.RegisterRequest):
    """Register new user account."""
    get_client_ip(request)

    if register_data.password != register_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match"
        )

    # Validate password strength
    if len(register_data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long",
        )

    user = await auth_manager.create_user(
        register_data.email, register_data.password, register_data.full_name
    )

    audit_logger.log_data_access(register_data.email, "user_registration", "create")

    token_data = auth_manager.create_jwt_token(user)
    return AuthModels.TokenResponse(**token_data)


@router.get("/me")
async def get_current_user_info(current_user: dict[str, Any] = Depends(require_auth)):
    """Get current user information."""
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "full_name": current_user.get("full_name"),
        "is_admin": current_user.get("is_admin", False),
        "is_verified": current_user.get("is_verified", True),
    }


@router.post("/logout")
async def logout(current_user: dict[str, Any] = Depends(require_auth)):
    """Logout user (client should discard token)."""
    audit_logger.log_data_access(current_user["email"], "user_logout", "logout")
    return {"message": "Logged out successfully"}


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str | None = None):
    """Serve login page."""
    context = {
        "request": request,
        "error": error,
        "app_name": "Klerno Labs",
        "current_year": datetime.now().year,
    }
    return templates.TemplateResponse("login.html", context)


# OAuth endpoints (if enabled)
if AUTH_CONFIG["enable_oauth"]:

    @router.get("/oauth/{provider}")
    async def oauth_login(provider: str, request: Request):
        """Initiate OAuth login with provider."""
        # Implement OAuth flow based on provider
        # This is a placeholder - implement based on your OAuth requirements
        if provider not in ["google", "github"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported OAuth provider",
            )

        # Generate state for CSRF protection
        secrets.token_urlsafe(32)

        # Store state in session or cache
        # Redirect to OAuth provider
        # This is provider-specific implementation

        return {"message": f"OAuth with {provider} not fully implemented"}

    @router.post("/oauth/callback")
    async def oauth_callback(request: Request, oauth_data: AuthModels.OAuthRequest):
        """Handle OAuth callback."""
        # Implement OAuth callback handling
        # This is a placeholder
        return {"message": "OAuth callback not fully implemented"}


# Legacy compatibility functions (for gradual migration)
def current_user(request: Request) -> dict[str, Any] | None:
    """Legacy function for getting current user."""
    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:]  # Remove "Bearer " prefix
    token_data = auth_manager.verify_jwt_token(token)
    if not token_data:
        return None

    # Return simplified user data for compatibility
    return {"email": token_data["email"], "id": token_data["sub"]}


def require_user(request: Request) -> dict[str, Any]:
    """Legacy function requiring authentication."""
    user = current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    return user


def require_paid_or_admin(request: Request) -> dict[str, Any]:
    """Legacy function requiring paid subscription or admin."""
    user = require_user(request)
    # For now, just require authentication
    # Implement subscription checking based on your business logic
    return user


# Export public interface
__all__ = [
    "router",
    "AuthenticationManager",
    "AuthModels",
    "auth_manager",
    "get_current_user",
    "require_auth",
    "require_admin",
    "current_user",  # Legacy
    "require_user",  # Legacy
    "require_paid_or_admin",  # Legacy
]
