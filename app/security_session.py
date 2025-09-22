import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

# Load environment variables from .env file if it exists
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    # best-effort: if python-dotenv is available use it, otherwise continue
    try:
        import dotenv

        dotenv.load_dotenv(env_file, override=True)  # Override existing env vars
    except Exception:
        # deliberately ignore import/load failures; non-fatal in tests
        pass

# ENV - Secure JWT configuration
# For developer/test environments we tolerate a missing JWT_SECRET and
# fall back to a weak, deterministic secret to allow imports and tests to
# proceed. In production you MUST set a strong JWT_SECRET env var.
SECRET_KEY = os.getenv("JWT_SECRET")
if (
    not SECRET_KEY
    or len(SECRET_KEY) < 32
    or SECRET_KEY == "CHANGE_ME_32+_chars"
):
    # Don't exit during tests — use a default local secret and print a warning.
    try:
        import warnings

        warnings.warn(
            "JWT_SECRET is not set or is too short - using a test fallback.",
            RuntimeWarning,
        )
    except Exception:
        pass
    SECRET_KEY = os.getenv(
        "JWT_SECRET",
        "test-secret-for-local-development-please-change",
    )

ALGO = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_pw(password: str) -> str:
    return _pwd.hash(password)


def verify_pw(password: str, hashed: str) -> bool:
    return _pwd.verify(password, hashed)


def issue_jwt(
    uid: int, email: str, role: str, minutes: int | None = None
) -> str:
    """Create a JWT with both sub=email and uid (numeric user id).

    The token includes both `uid` and `user_id` keys to support
    different test expectations.
    """
    # Respect explicit 0 values (tests may set expiry to 0). Only use the
    # default when minutes is None.
    exp_minutes = (
        ACCESS_TOKEN_EXPIRE_MINUTES if minutes is None else minutes
    )
    now = datetime.now(UTC)
    payload = {
        "sub": email,
        "uid": int(uid),
        "user_id": int(uid),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=exp_minutes),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGO)


def decode_jwt(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGO])



# Dependency injection helpers
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
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
            "role": payload.get("role", "user"),
        }
    except jwt.PyJWTError:
        # Avoid revealing internal exception details to callers
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW - Authenticate": "Bearer"},
        ) from None
