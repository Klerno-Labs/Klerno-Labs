#!/usr/bin/env python3
"""Comprehensive input validation and sanitization framework."""

import re
import html
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, validator, Field
import logging

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom validation error."""
    pass

class InputSanitizer:
    """Comprehensive input sanitization utilities."""
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """Sanitize string input to prevent XSS and injection attacks."""
        
        if not isinstance(value, str):
            raise ValidationError("Input must be a string")
        
        # Limit length
        if len(value) > max_length:
            raise ValidationError(f"Input too long (max {max_length} characters)")
        
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
                raise ValidationError("Potentially dangerous input detected")
        
        return sanitized
    
    @staticmethod
    def sanitize_email(email: str) -> str:
        """Validate and sanitize email address."""
        
        email = email.strip().lower()
        
        # Basic email pattern
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, email):
            raise ValidationError("Invalid email format")
        
        # Additional security checks
        if len(email) > 254:  # RFC 5321 limit
            raise ValidationError("Email address too long")
        
        return email
    
    @staticmethod
    def sanitize_integer(value: Union[str, int], min_val: int = None, max_val: int = None) -> int:
        """Validate and sanitize integer input."""
        
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            raise ValidationError("Invalid integer value")
        
        if min_val is not None and int_value < min_val:
            raise ValidationError(f"Value must be at least {min_val}")
        
        if max_val is not None and int_value > max_val:
            raise ValidationError(f"Value must be at most {max_val}")
        
        return int_value
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent path traversal attacks."""
        
        if not isinstance(filename, str):
            raise ValidationError("Filename must be a string")
        
        # Remove path separators and dangerous characters
        dangerous_chars = ['/', '\\', '..', ':', '*', '?', '"', '<', '>', '|']
        
        sanitized = filename
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        # Ensure filename is not empty and not too long
        sanitized = sanitized.strip()
        if not sanitized:
            raise ValidationError("Invalid filename")
        
        if len(sanitized) > 255:
            raise ValidationError("Filename too long")
        
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
    
    @validator('username')
    def validate_username(cls, v):
        """Validate username format."""
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError("Username can only contain letters, numbers, and underscores")
        return InputSanitizer.sanitize_string(v)
    
    @validator('email')
    def validate_email(cls, v):
        """Validate email format."""
        return InputSanitizer.sanitize_email(v)
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        
        # Check password complexity
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter")
        
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter")
        
        if not re.search(r'\d', v):
            raise ValueError("Password must contain at least one digit")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError("Password must contain at least one special character")
        
        return v  # Don't sanitize passwords

class SearchQueryModel(SecureBaseModel):
    """Secure search query model."""
    
    query: str = Field(..., min_length=1, max_length=500)
    limit: Optional[int] = Field(default=10, ge=1, le=100)
    offset: Optional[int] = Field(default=0, ge=0)
    
    @validator('query')
    def validate_query(cls, v):
        """Validate search query."""
        return InputSanitizer.sanitize_string(v, max_length=500)

def validate_request_size(content_length: Optional[str], max_size: int = 10 * 1024 * 1024) -> None:
    """Validate request content size to prevent DoS attacks."""
    
    if content_length:
        try:
            size = int(content_length)
            if size > max_size:
                raise ValidationError(f"Request too large (max {max_size} bytes)")
        except ValueError:
            raise ValidationError("Invalid content length")

# Example usage:
# from input_validation import UserCreateModel, InputSanitizer, validate_request_size
# 
# @app.post("/users")
# async def create_user(user_data: UserCreateModel):
#     # Input is automatically validated and sanitized
#     return {"message": "User created successfully"}
