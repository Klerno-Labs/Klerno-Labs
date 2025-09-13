"""
Unit tests for authentication and security functionality.
"""
import pytest
from unittest.mock import patch, MagicMock
from app.security import enforce_api_key, expected_api_key, generate_api_key
from app.security_session import hash_pw, verify_pw, issue_jwt
from app.settings import get_settings


class TestAPISecurity:
    """Test API key authentication."""

    def test_generate_api_key(self):
        """Test API key generation."""
        key = generate_api_key()
        assert isinstance(key, str)
        assert len(key) > 10

    @patch.dict('os.environ', {'API_KEY': 'test-key'})
    def test_expected_api_key(self):
        """Test expected API key from environment."""
        key = expected_api_key()
        assert key == 'test-key'

    def test_generate_api_key_randomness(self):
        """Test that generated API keys are unique."""
        key1 = generate_api_key()
        key2 = generate_api_key()
        assert key1 != key2
        assert len(key1) == len(key2)


class TestPasswordSecurity:
    """Test password hashing and verification."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "test_password_123"
        hashed = hash_pw(password)
        assert isinstance(hashed, str)
        assert hashed != password
        assert len(hashed) > 50  # Bcrypt hashes are long

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "test_password_123"
        hashed = hash_pw(password)
        assert verify_pw(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = hash_pw(password)
        assert verify_pw(wrong_password, hashed) is False

    def test_verify_password_empty(self):
        """Test password verification with empty password."""
        password = "test_password_123"
        hashed = hash_pw(password)
        assert verify_pw("", hashed) is False


class TestJWTSecurity:
    """Test JWT token functionality."""

    def test_issue_jwt(self):
        """Test JWT token creation."""
        uid = 1
        email = "test@example.com"
        role = "user"
        token = issue_jwt(uid, email, role)
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are long
        assert '.' in token  # JWT has dots as separators

    def test_issue_jwt_with_custom_expiry(self):
        """Test JWT token creation with custom expiry."""
        uid = 1
        email = "test@example.com"
        role = "admin"
        custom_minutes = 120
        token = issue_jwt(uid, email, role, custom_minutes)
        assert isinstance(token, str)
        assert len(token) > 50