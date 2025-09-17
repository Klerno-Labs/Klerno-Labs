#!/usr/bin/env python3
"""
🔐 SECURE CREDENTIALS GENERATOR FOR KLERNO LABS
Generates cryptographically secure passwords and keys for top 0.01% security
"""

import secrets
import string
import os
from cryptography.fernet import Fernet
import base64

def generate_secure_api_key(prefix="sk-", length=64):
    """Generate secure API key"""
    key = base64.b64encode(os.urandom(length)).decode('utf-8').replace('=', '').replace('+', '').replace('/', '')[:length]
    return f"{prefix}{key}"

def generate_secure_password(length=32):
    """Generate secure password with mixed characters"""
    chars = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
    return ''.join(secrets.choice(chars) for _ in range(length))

def generate_hex_secret(length=64):
    """Generate hex secret"""
    return secrets.token_hex(length)

def generate_url_safe_secret(length=64):
    """Generate URL-safe secret"""
    return secrets.token_urlsafe(length)

def generate_encryption_key():
    """Generate Fernet encryption key"""
    return Fernet.generate_key().decode()

def main():
    """Generate all secure credentials"""
    print("🔐 GENERATING ULTRA-SECURE CREDENTIALS FOR KLERNO LABS")
    print("=" * 70)
    print()
    
    credentials = {
        "X_API_KEY": generate_secure_api_key("sk-", 128),
        "SECRET_KEY": generate_url_safe_secret(64),
        "JWT_SECRET": generate_hex_secret(64),
        "ENCRYPTION_KEY": generate_encryption_key(),
        "WEBHOOK_SECRET": generate_hex_secret(32),
        "SESSION_SECRET": generate_url_safe_secret(64),
        "PAYWALL_CODE": generate_url_safe_secret(16),
        "ADMIN_PASSWORD": generate_secure_password(32),
        "DATABASE_PASSWORD": generate_url_safe_secret(32),
        "BACKUP_ENCRYPTION_KEY": generate_encryption_key(),
        "AUDIT_LOG_KEY": generate_hex_secret(32),
        "RATE_LIMIT_SECRET": generate_url_safe_secret(32),
        "CSRF_SECRET": generate_hex_secret(32),
    }
    
    print("📋 COPY THESE TO YOUR .env FILE:")
    print("-" * 70)
    for key, value in credentials.items():
        print(f"{key}={value}")
    
    print()
    print("🛡️ ADDITIONAL SECURITY RECOMMENDATIONS:")
    print("1. Store these in a secure password manager")
    print("2. Never commit these to version control")
    print("3. Rotate every 90 days")
    print("4. Use different keys for production/staging")
    print("5. Enable monitoring for key usage")
    
    # Save to secure file
    with open('.env.secure', 'w', encoding='utf-8') as f:
        f.write("# ULTRA-SECURE CREDENTIALS FOR KLERNO LABS\n")
        f.write("# Generated with cryptographically secure random generators\n")
        f.write("# NEVER COMMIT THIS FILE TO VERSION CONTROL\n\n")
        
        for key, value in credentials.items():
            f.write(f"{key}={value}\n")
    
    print(f"\n✅ Credentials saved to .env.secure")
    print("⚠️  Remember to add .env.secure to .gitignore!")

if __name__ == "__main__":
    main()