"""
Multi-Factor Authentication (MFA) core logic for Klerno Labs.
Supports TOTP, WebAuthn, and hardware key enforcement for admins.
"""
import os
import pyotp
from typing import Optional
from cryptography.fernet import Fernet

MFA_ENCRYPTION_KEY = os.getenv("MFA_ENCRYPTION_KEY", Fernet.generate_key().decode())
fernet = Fernet(MFA_ENCRYPTION_KEY.encode())

# TOTP (Time-based One-Time Password)
def generate_totp_secret() -> str:
    return pyotp.random_base32()

def get_totp_uri(email: str, secret: str, issuer: str = "Klerno Labs") -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)

def verify_totp(token: str, secret: str) -> bool:
    return pyotp.TOTP(secret).verify(token, valid_window=1)

def encrypt_seed(seed: str) -> str:
    return fernet.encrypt(seed.encode()).decode()

def decrypt_seed(token: str) -> str:
    return fernet.decrypt(token.encode()).decode()

# Placeholder for WebAuthn/passkey logic (to be implemented)
def verify_webauthn(*args, **kwargs):
    raise NotImplementedError("WebAuthn/passkey support not yet implemented.")

def enforce_admin_hardware_key(user) -> bool:
    # Placeholder: check if admin has registered hardware key
    return user.get("role") == "admin" and user.get("has_hardware_key", False)
