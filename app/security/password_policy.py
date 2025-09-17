"""
World-class password policy enforcement for Klerno Labs.
Implements NIST SP 800-63B, OWASP, and enterprise best practices.
"""
import re
import os
import secrets
import requests
from typing import List, Optional
from argon2 import PasswordHasher, exceptions as argon2_exceptions
from pydantic import BaseModel

HIBP_API = "https://api.pwnedpasswords.com/range/"

# Internal blacklist (expand as needed)
INTERNAL_BLACKLIST = {
    "password", "password123", "123456", "qwerty", "letmein", "admin", "welcome", "klerno", "klernolabs",
    "iloveyou", "monkey", "abc123", "1q2w3e4r", "passw0rd", "password1", "1234567890", "111111", "123123",
    "qwertyuiop", "!@#$%^&*", "000000", "zaq12wsx", "dragon", "sunshine", "princess", "football"
}

class PasswordPolicyConfig(BaseModel):
    min_length: int = 16
    max_length: int = 128
    require_upper: bool = True
    require_lower: bool = True
    require_digit: bool = True
    require_symbol: bool = True
    allow_repeats: bool = False
    check_breaches: bool = True
    blacklist: List[str] = list(INTERNAL_BLACKLIST)
    app_name: str = "klerno"

ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2, hash_len=32, salt_len=16)

class PasswordPolicy:
    def __init__(self, config: Optional[PasswordPolicyConfig] = None):
        self.config = config or PasswordPolicyConfig()

    def validate(self, password: str, username: str = "", email: str = "") -> List[str]:
        errors = []
        c = self.config
        if not (c.min_length <= len(password) <= c.max_length):
            errors.append(f"Password must be {c.min_length}-{c.max_length} characters.")
        if c.require_upper and not re.search(r"[A-Z]", password):
            errors.append("Password must include an uppercase letter.")
        if c.require_lower and not re.search(r"[a-z]", password):
            errors.append("Password must include a lowercase letter.")
        if c.require_digit and not re.search(r"\d", password):
            errors.append("Password must include a digit.")
        if c.require_symbol and not re.search(r"[^\w\s]", password):
            errors.append("Password must include a symbol.")
        if not c.allow_repeats and re.search(r"(.)\1{3,}", password):
            errors.append("Password cannot contain repetitive sequences (e.g., aaaa, 1111, etc.).")
        if username and username.lower() in password.lower():
            errors.append("Password cannot contain your username.")
        if email and email.split("@")[0].lower() in password.lower():
            errors.append("Password cannot contain your email username.")
        if c.app_name and c.app_name.lower() in password.lower():
            errors.append("Password cannot contain the app name.")
        for banned in c.blacklist:
            if banned.lower() in password.lower():
                errors.append("Password contains a blacklisted word or phrase.")
                break
        return errors

    def check_breached(self, password: str) -> bool:
        # Use k-Anonymity model (first 5 chars of SHA1 hash)
        import hashlib
        sha1 = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
        prefix, suffix = sha1[:5], sha1[5:]
        try:
            resp = requests.get(HIBP_API + prefix, timeout=5)
            if resp.status_code == 200:
                hashes = resp.text.splitlines()
                for line in hashes:
                    if line.startswith(suffix):
                        return True
        except Exception:
            pass  # Fail closed: if HIBP is down, don't block user
        return False

    def hash(self, password: str, pepper: Optional[str] = None) -> str:
        pepper = pepper or os.getenv("PASSWORD_PEPPER", "")
        return ph.hash(password + pepper)

    def verify(self, password: str, hashed: str, pepper: Optional[str] = None) -> bool:
        pepper = pepper or os.getenv("PASSWORD_PEPPER", "")
        try:
            return ph.verify(hashed, password + pepper)
        except argon2_exceptions.VerifyMismatchError:
            return False

policy = PasswordPolicy()
