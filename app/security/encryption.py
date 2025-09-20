"""
Encryption Utilities for Sensitive Data
Provides secure encryption/decryption for sensitive information
"""

import base64
import json
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class DataEncryption:
    """Handles encryption/decryption of sensitive data"""

    def __init__(self, password: str | None = None):
        self.password = password or os.getenv(
            "ENCRYPTION_KEY", "default-dev-key-change-in-prod"
        )
        self._fernet = None

    @property
    def fernet(self) -> Fernet:
        """Get or create Fernet instance"""
        if self._fernet is None:
            key = self._derive_key(self.password)
            self._fernet = Fernet(key)
        return self._fernet

    def _derive_key(self, password: str) -> bytes:
        """Derive encryption key from password"""
        salt = b"klerno_salt_2024"  # In production, use random salt per user
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    def encrypt_data(self, data: str) -> str:
        """Encrypt string data"""
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt string data"""
        return self.fernet.decrypt(encrypted_data.encode()).decode()

    def encrypt_json(self, data: dict) -> str:
        """Encrypt JSON data"""
        json_str = json.dumps(data)
        return self.encrypt_data(json_str)

    def decrypt_json(self, encrypted_data: str) -> dict:
        """Decrypt JSON data"""
        json_str = self.decrypt_data(encrypted_data)
        return json.loads(json_str)


class SecureStorage:
    """Secure storage for sensitive configuration"""

    def __init__(self):
        self.encryption = DataEncryption()
        self.storage_file = ".secure_config"

    def store_secret(self, key: str, value: str):
        """Store encrypted secret"""
        data = self._load_storage()
        data[key] = self.encryption.encrypt_data(value)
        self._save_storage(data)

    def get_secret(self, key: str) -> str | None:
        """Retrieve and decrypt secret"""
        data = self._load_storage()
        encrypted_value = data.get(key)
        if encrypted_value:
            try:
                return self.encryption.decrypt_data(encrypted_value)
            except Exception:
                return None
        return None

    def _load_storage(self) -> dict:
        """Load encrypted storage file"""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file) as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_storage(self, data: dict):
        """Save encrypted storage file"""
        with open(self.storage_file, "w") as f:
            json.dump(data, f)


def generate_secure_token(length: int = 32) -> str:
    """Generate cryptographically secure random token"""
    return secrets.token_urlsafe(length)


def hash_password(password: str) -> str:
    """Securely hash password"""
    import bcrypt

    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    import bcrypt

    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
