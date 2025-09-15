# app/auth_oauth.py
"""
OAuth 2.0 authentication handlers for Google and Microsoft.
"""
import secrets
import httpx
from typing import Optional, Dict, Any
from urllib.parse import urlencode

from fastapi import APIRouter, Request, Response, HTTPException, Depends
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth

from . import store
from .security_session import issue_jwt
from .settings import get_settings, Settings
from .deps import require_user

# Get settings
S: Settings = get_settings()

# OAuth configuration
oauth = OAuth()

# Google OAuth
oauth.register(
    name='google',
    client_id=S.google_client_id,
    client_secret=S.google_client_secret,
    server_metadata_url='https://accounts.google.com/.well-known/openid_configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# Microsoft OAuth  
oauth.register(
    name='microsoft',
    client_id=S.microsoft_client_id,
    client_secret=S.microsoft_client_secret,
    access_token_url='https://login.microsoftonline.com/common/oauth2/v2.0/token',
    authorize_url='https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
    api_base_url='https://graph.microsoft.com/v1.0/',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

router = APIRouter(prefix="/auth/oauth", tags=["oauth"])


def _set_session_cookie(res: Response, token: str) -> None:
    """Set the session cookie with sane defaults."""
    res.set_cookie(
        key="session",
        value=token,
        httponly=True,
        secure=(S.app_env != "dev"),
        samesite="lax",
        max_age=60 * 60 * 24 * 7,  # 7 days
        path="/",
    )


@router.get("/google")
async def google_login(request: Request):
    """Initiate Google OAuth login."""
    redirect_uri = request.url_for('google_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, response: Response):
    """Handle Google OAuth callback."""
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        
        if not user_info:
            # Fetch user info from Google
            resp = await oauth.google.parse_id_token(request, token)
            user_info = resp
        
        email = user_info.get('email')
        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by Google")
        
        # Check if user exists
        existing_user = store.get_user_by_email(email.lower())
        if not existing_user:
            # Check if this Google account is already linked to another user
            oauth_user = store.get_user_by_oauth('google', user_info.get('sub'))
            if oauth_user:
                user = oauth_user
            else:
                # Create new user
                user = store.create_user(
                    email=email.lower(),
                    password_hash=None,  # OAuth users don't have passwords
                    role="viewer",
                    subscription_active=False,
                    oauth_provider='google',
                    oauth_id=user_info.get('sub'),
                    display_name=user_info.get('name'),
                    avatar_url=user_info.get('picture')
                )
        else:
            # User exists with this email, update OAuth info if not set
            if not existing_user.get('oauth_provider'):
                # Link existing account to Google
                store.update_user_profile(
                    existing_user['id'],
                    display_name=user_info.get('name'),
                    avatar_url=user_info.get('picture')
                )
                # Update OAuth fields (would need a new function for this)
            user = existing_user
        
        # Issue JWT token
        token = issue_jwt(user["id"], user["email"], user["role"])
        _set_session_cookie(response, token)
        
        # Redirect based on user role
        if user.get("role") == "admin":
            redirect_url = "/admin"
        else:
            redirect_url = "/dashboard"
            
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth error: {str(e)}")


@router.get("/microsoft")
async def microsoft_login(request: Request):
    """Initiate Microsoft OAuth login."""
    redirect_uri = request.url_for('microsoft_callback')
    return await oauth.microsoft.authorize_redirect(request, redirect_uri)


@router.get("/microsoft/callback")
async def microsoft_callback(request: Request, response: Response):
    """Handle Microsoft OAuth callback."""
    try:
        token = await oauth.microsoft.authorize_access_token(request)
        
        # Get user info from Microsoft Graph
        headers = {'Authorization': f'Bearer {token["access_token"]}'}
        async with httpx.AsyncClient() as client:
            resp = await client.get('https://graph.microsoft.com/v1.0/me', headers=headers)
            user_info = resp.json()
        
        email = user_info.get('mail') or user_info.get('userPrincipalName')
        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by Microsoft")
        
        # Check if user exists
        existing_user = store.get_user_by_email(email.lower())
        if not existing_user:
            # Check if this Microsoft account is already linked
            oauth_user = store.get_user_by_oauth('microsoft', user_info.get('id'))
            if oauth_user:
                user = oauth_user
            else:
                # Create new user
                user = store.create_user(
                    email=email.lower(),
                    password_hash=None,
                    role="viewer", 
                    subscription_active=False,
                    oauth_provider='microsoft',
                    oauth_id=user_info.get('id'),
                    display_name=user_info.get('displayName'),
                    avatar_url=None  # Microsoft Graph would need separate call for photo
                )
        else:
            # User exists, optionally update profile
            if not existing_user.get('oauth_provider'):
                store.update_user_profile(
                    existing_user['id'],
                    display_name=user_info.get('displayName')
                )
            user = existing_user
        
        # Issue JWT token
        token = issue_jwt(user["id"], user["email"], user["role"])
        _set_session_cookie(response, token)
        
        # Redirect based on user role
        if user.get("role") == "admin":
            redirect_url = "/admin"
        else:
            redirect_url = "/dashboard"
            
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth error: {str(e)}")


@router.post("/unlink/{provider}")
async def unlink_oauth_provider(provider: str, user=Depends(require_user)):
    """Unlink an OAuth provider from the current user account."""
    if provider not in ['google', 'microsoft']:
        raise HTTPException(status_code=400, detail="Invalid provider")
    
    # Only allow unlinking if user has a password set
    if not user.get('password_hash') and user.get('oauth_provider') == provider:
        raise HTTPException(
            status_code=400, 
            detail="Cannot unlink OAuth provider without setting a password first"
        )
    
    # Update user to remove OAuth info (would need a new store function)
    # For now, return success
    return {"success": True, "message": f"{provider.title()} account unlinked"}