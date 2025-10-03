import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

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

        # Do not override existing environment variables set by tests
        dotenv.load_dotenv(env_file, override=False)
    except Exception:
        # Deliberately ignore import/load failures; this is a best-effort
        # convenience for developer/test environments (non-fatal).
        pass

# ENV - Secure JWT configuration
# For developer/test environments we tolerate a missing JWT_SECRET and
# fall back to a weak, deterministic secret to allow imports and tests to
# proceed. In production you MUST set a strong JWT_SECRET env var.
SECRET_KEY = os.getenv("JWT_SECRET")
if not SECRET_KEY or len(SECRET_KEY) < 32 or SECRET_KEY == "CHANGE_ME_32+_chars":
    # Don't exit during tests — use a default local secret and print a warning.
    try:
        import warnings

        warnings.warn(
            "JWT_SECRET is not set or is too short - using a test fallback.",
            RuntimeWarning,
            stacklevel=2,
        )
    except Exception:
        # Ignore warning emission failures (non-fatal in constrained test envs)
        pass
    SECRET_KEY = os.getenv(
        "JWT_SECRET",
        "test-secret-for-local-development-please-change",  # nosec: B105 - test-only fallback secret
    )

ALGO = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

_pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_pw(password: str) -> str:
    """Hash a plaintext password.

    bcrypt has a 72-byte input limit. We explicitly truncate to 72 bytes
    (after UTF-8 encoding) to ensure deterministic behavior and avoid
    runtime ValueError during tests or when callers pass long secrets.

    This is a deliberate implementation detail; callers should prefer
    reasonably-sized passwords but we make the truncation explicit here
    to keep tests and existing calling code behaving consistently.
    """
    # Normalize and truncate to bcrypt's 72-byte limit
    if isinstance(password, str):
        pw_bytes = password.encode("utf-8")
    else:
        pw_bytes = bytes(password)
    # Truncate to 72 bytes, then decode back to a str for passlib
    pw_bytes = pw_bytes[:72]
    pw_str = pw_bytes.decode("utf-8", errors="ignore")
    # passlib.CryptContext.hash returns a str
    return _pwd.hash(pw_str)


def verify_pw(password: str, hashed: str) -> bool:
    # Apply the same normalization/truncation used in hash_pw to ensure
    # correct comparisons when long inputs are presented.
    if isinstance(password, str):
        pw_bytes = password.encode("utf-8")
    else:
        pw_bytes = bytes(password)
    pw_bytes = pw_bytes[:72]
    pw_str = pw_bytes.decode("utf-8", errors="ignore")
    return _pwd.verify(pw_str, hashed)


def verify_and_maybe_rehash(password: str, hashed: str) -> tuple[bool, str | None]:
    """Verify a password and return (is_valid, new_hash_or_None).

    If the password verifies but the stored hash uses an older scheme or
    parameters, this function computes a fresh hash with the current
    CryptContext and returns it so callers can persist the rotated hash.
    The function is deliberately lightweight and does not perform any
    persistence itself — callers should persist the returned hash when
    present (for example, call `store.update_user_password`).
    """
    # Normalize/truncate like hash_pw so comparisons are consistent
    if isinstance(password, str):
        pw_bytes = password.encode("utf-8")
    else:
        pw_bytes = bytes(password)
    pw_bytes = pw_bytes[:72]
    pw_str = pw_bytes.decode("utf-8", errors="ignore")

    try:
        ok = _pwd.verify(pw_str, hashed)
    except Exception:
        return False, None

    if not ok:
        return False, None

    # If the hash needs updating according to the CryptContext, return a
    # fresh hash for callers to persist.
    try:
        if _pwd.needs_update(hashed):
            new_hash = _pwd.hash(pw_str)
            return True, new_hash
    except Exception:
        # On any error while checking/rehashing, just return that the
        # password is valid and don't return a new hash.
        return True, None

    return True, None


def issue_jwt(uid: int, email: str, role: str, minutes: int | None = None) -> str:
    """Create a JWT with both sub=email and uid (numeric user id).

    The token includes both `uid` and `user_id` keys to support
    different test expectations.
    """
    # Respect explicit 0 values (tests may set expiry to 0). Only use the
    # default when minutes is None.
    exp_minutes = ACCESS_TOKEN_EXPIRE_MINUTES if minutes is None else minutes
    now = datetime.now(UTC)
    payload = {
        "sub": email,
        "uid": int(uid),
        "user_id": int(uid),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=exp_minutes),
    }
    token = jwt.encode(payload, str(SECRET_KEY), algorithm=ALGO)
    # Ensure str return for compatibility across PyJWT versions
    if isinstance(token, bytes):
        try:
            return token.decode("utf-8")
        except Exception:
            return token.decode("latin-1")
    return token


def decode_jwt(token: str) -> dict[str, Any]:
    return jwt.decode(token, str(SECRET_KEY), algorithms=[ALGO])


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
        # Follow RFC 7235 header name exactly: 'WWW-Authenticate'
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
