#!/usr/bin/env python3
"""JWT-based authentication framework for FastAPI."""

import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

logger = logging.getLogger(__name__)

class AuthenticationManager:
    """JWT-based authentication manager."""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256", expiration_hours: int = 24):
        """Initialize authentication manager."""
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expiration_hours = expiration_hours
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    def create_access_token(self, user_id: str, username: str, roles: list = None) -> str:
        """Create JWT access token."""
        
        if roles is None:
            roles = ["user"]
        
        expiration = datetime.utcnow() + timedelta(hours=self.expiration_hours)
        
        payload = {
            "user_id": user_id,
            "username": username,
            "roles": roles,
            "exp": expiration,
            "iat": datetime.utcnow(),
            "type": "access_token"
        }
        
        try:
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            return token
        except Exception as e:
            logger.error(f"Token creation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create access token"
            )
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token."""
        
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check token type
            if payload.get("type") != "access_token":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not verify token"
            )
    
    def create_refresh_token(self, user_id: str) -> str:
        """Create JWT refresh token."""
        
        expiration = datetime.utcnow() + timedelta(days=30)  # Longer expiration
        
        payload = {
            "user_id": user_id,
            "exp": expiration,
            "iat": datetime.utcnow(),
            "type": "refresh_token"
        }
        
        try:
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            return token
        except Exception as e:
            logger.error(f"Refresh token creation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create refresh token"
            )

class JWTBearer(HTTPBearer):
    """JWT Bearer token authentication."""
    
    def __init__(self, auth_manager: AuthenticationManager, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)
        self.auth_manager = auth_manager
    
    async def __call__(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication scheme"
                )
            
            token_data = self.auth_manager.verify_token(credentials.credentials)
            return token_data
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization credentials"
            )

def require_roles(required_roles: list):
    """Decorator to require specific roles."""
    
    def decorator(func):
        def wrapper(current_user: dict, *args, **kwargs):
            user_roles = current_user.get("roles", [])
            
            # Check if user has any of the required roles
            if not any(role in user_roles for role in required_roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required roles: {required_roles}"
                )
            
            return func(current_user, *args, **kwargs)
        return wrapper
    
    return decorator

# Example usage:
# from auth_framework import AuthenticationManager, JWTBearer, require_roles
# 
# # Initialize authentication
# auth_manager = AuthenticationManager(secret_key="your-secret-key")
# jwt_bearer = JWTBearer(auth_manager)
# 
# @app.post("/login")
# async def login(username: str, password: str):
#     # Verify user credentials (implement your user lookup)
#     if verify_user_credentials(username, password):
#         token = auth_manager.create_access_token(
#             user_id="123",
#             username=username,
#             roles=["user"]
#         )
#         return {"access_token": token, "token_type": "bearer"}
#     raise HTTPException(status_code=401, detail="Invalid credentials")
# 
# @app.get("/protected")
# async def protected_endpoint(current_user: dict = Depends(jwt_bearer)):
#     return {"message": f"Hello {current_user['username']}"}
# 
# @app.get("/admin")
# @require_roles(["admin"])
# async def admin_endpoint(current_user: dict = Depends(jwt_bearer)):
#     return {"message": "Admin access granted"}
