# app/security_session.py
import os
from datetime import datetime, timedelta, timezone
import jwt
from passlib.context import CryptContext

# ENV
SECRET_KEY = os.getenv("JWT_SECRET", "CHANGE_ME_32+_chars")
ALGO = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_pw(password: str) -> str:
    return _pwd.hash(password)

def verify_pw(password: str, hashed: str) -> bool:
    return _pwd.verify(password, hashed)

def issue_jwt(uid: int, email: str, role: str, minutes: int | None = None) -> str:
    """
    Create a JWT with both sub=email (common) and uid=<int> (your store lookups),
    plus role for convenience.
    """
    exp_minutes = minutes or ACCESS_TOKEN_EXPIRE_MINUTES
    now = datetime.now(timezone.utc)
    payload = {
        "sub": email,          # email as primary subject
        "uid": int(uid),       # numeric user id for your store
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=exp_minutes),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGO)

def decode_jwt(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGO])

# Add get_current_user function for dependency injection
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Extracts and validates the JWT token from the request.
    Returns the user information if valid.
    """
    token = credentials.credentials
    try:
        payload = decode_jwt(token)
        return {
            "uid": payload.get("uid"),
            "email": payload.get("sub"),
            "role": payload.get("role", "user")
        }
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )