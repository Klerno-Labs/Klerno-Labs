#!/usr/bin/env python3
"""Comprehensive input validation and sanitization framework."""

import html
import logging
import re

from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom validation error."""


class InputSanitizer:
    """Comprehensive input sanitization utilities."""

    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """Sanitize string input to prevent XSS and injection attacks."""
        if not isinstance(value, str):
            msg = "Input must be a string"
            raise ValidationError(msg)

        # Limit length
        if len(value) > max_length:
            msg = f"Input too long (max {max_length} characters)"
            raise ValidationError(msg)

        # HTML escape
        sanitized = html.escape(value)

        # Remove potential SQL injection patterns
        dangerous_patterns = [
            r"'\s*(or|and)\s*'\s*=\s*'",  # SQL injection patterns
            r"union\s+select",
            r"drop\s+table",
            r"delete\s+from",
            r"insert\s+into",
            r"update\s+.+\s+set",
            r"exec(ute)?\s*\(",
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, sanitized, re.IGNORECASE):
                msg = "Potentially dangerous input detected"
                raise ValidationError(msg)

        return sanitized

    @staticmethod
    def sanitize_email(email: str) -> str:
        """Validate and sanitize email address."""
        email = email.strip().lower()

        # Basic email pattern
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        if not re.match(email_pattern, email):
            msg = "Invalid email format"
            raise ValidationError(msg)

        # Additional security checks
        if len(email) > 254:  # RFC 5321 limit
            msg = "Email address too long"
            raise ValidationError(msg)

        return email

    @staticmethod
    def sanitize_integer(
        value: str | int,
        min_val: int | None = None,
        max_val: int | None = None,
    ) -> int:
        """Validate and sanitize integer input."""
        try:
            int_value = int(value)
        except (ValueError, TypeError) as e:
            msg = "Invalid integer value"
            raise ValidationError(msg) from e

        if min_val is not None and int_value < min_val:
            msg = f"Value must be at least {min_val}"
            raise ValidationError(msg)

        if max_val is not None and int_value > max_val:
            msg = f"Value must be at most {max_val}"
            raise ValidationError(msg)

        return int_value

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent path traversal attacks."""
        if not isinstance(filename, str):
            msg = "Filename must be a string"
            raise ValidationError(msg)

        # Remove path separators and dangerous characters
        dangerous_chars = ["/", "\\", "..", ":", "*", "?", '"', "<", ">", "|"]

        sanitized = filename
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, "")

        # Ensure filename is not empty and not too long
        sanitized = sanitized.strip()
        if not sanitized:
            msg = "Invalid filename"
            raise ValidationError(msg)

        if len(sanitized) > 255:
            msg = "Filename too long"
            raise ValidationError(msg)

        return sanitized


class SecureBaseModel(BaseModel):
    """Base Pydantic model with enhanced security validation."""

    class Config:
        """Pydantic configuration."""

        validate_assignment = True
        extra = "forbid"  # Prevent additional fields
        max_anystr_length = 10000  # Global string length limit


class UserCreateModel(SecureBaseModel):
    """Secure user creation model."""

    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., max_length=254)
    password: str = Field(..., min_length=8, max_length=128)

    @validator("username")
    def validate_username(self, v):
        """Validate username format."""
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            msg = "Username can only contain letters, numbers, and underscores"
            raise ValueError(
                msg,
            )
        return InputSanitizer.sanitize_string(v)

    @validator("email")
    def validate_email(self, v):
        """Validate email format."""
        return InputSanitizer.sanitize_email(v)

    @validator("password")
    def validate_password(self, v):
        """Validate password strength."""
        # Check password complexity
        if not re.search(r"[A-Z]", v):
            msg = "Password must contain at least one uppercase letter"
            raise ValueError(msg)

        if not re.search(r"[a-z]", v):
            msg = "Password must contain at least one lowercase letter"
            raise ValueError(msg)

        if not re.search(r"\d", v):
            msg = "Password must contain at least one digit"
            raise ValueError(msg)

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            msg = "Password must contain at least one special character"
            raise ValueError(msg)

        return v  # Don't sanitize passwords


class SearchQueryModel(SecureBaseModel):
    """Secure search query model."""

    query: str = Field(..., min_length=1, max_length=500)
    limit: int | None = Field(default=10, ge=1, le=100)
    offset: int | None = Field(default=0, ge=0)

    @validator("query")
    def validate_query(self, v):
        """Validate search query."""
        return InputSanitizer.sanitize_string(v, max_length=500)


def validate_request_size(
    content_length: str | None,
    max_size: int = 10 * 1024 * 1024,
) -> None:
    """Validate request content size to prevent DoS attacks."""
    if content_length:
        try:
            size = int(content_length)
            if size > max_size:
                msg = f"Request too large (max {max_size} bytes)"
                raise ValidationError(msg)
        except ValueError as e:
            msg = "Invalid content length"
            raise ValidationError(msg) from e


# Example usage:
# from input_validation import UserCreateModel, InputSanitizer, validate_request_size
#
# @app.post("/users")
# async def create_user(user_data: UserCreateModel):
#     # Input is automatically validated and sanitized
#     return {"message": "User created successfully"}
