#!/usr/bin/env python3
"""
Security Setup Script for Klerno Labs
Generates secure secrets and validates security configuration.
"""

import os
import secrets
import string
from pathlib import Path

def generate_secure_secret(length=32):
    """Generate a cryptographically secure secret key."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def create_env_file():
    """Create .env file with secure defaults if it doesn't exist."""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if env_file.exists():
        print("✅ .env file already exists")
        return
    
    if not env_example.exists():
        print("❌ .env.example file not found")
        return
    
    # Read example file
    with open(env_example, 'r') as f:
        content = f.read()
    
    # Generate secure secrets
    jwt_secret = secrets.token_hex(32)  # 64 chars hex
    secret_key = secrets.token_hex(32)  # 64 chars hex
    password_pepper = secrets.token_hex(32)  # 64 chars hex
    api_key = secrets.token_hex(16)  # 32 chars hex
    
    # Replace placeholders with actual secrets
    content = content.replace(
        "your_super_secure_jwt_secret_key_at_least_32_chars_long", 
        jwt_secret
    )
    content = content.replace(
        "your_application_secret_key_for_sessions_32_chars_min", 
        secret_key
    )
    content = content.replace(
        "your_password_pepper_32_chars_minimum", 
        password_pepper
    )
    content = content.replace(
        "your_production_api_key_here", 
        api_key
    )
    
    # Write to .env file
    with open(env_file, 'w') as f:
        f.write(content)
    
    print("✅ Created .env file with secure secrets")
    print("📝 Please review and update the .env file with your specific configuration")

def validate_jwt_secret():
    """Validate that JWT_SECRET is properly configured."""
    jwt_secret = os.getenv("JWT_SECRET")
    
    if not jwt_secret:
        print("❌ JWT_SECRET environment variable not set")
        return False
    
    if len(jwt_secret) < 32:
        print(f"❌ JWT_SECRET too short ({len(jwt_secret)} chars). Minimum 32 characters required.")
        return False
    
    if jwt_secret in ["CHANGE_ME_32+_chars", "your_super_secure_jwt_secret_key_at_least_32_chars_long"]:
        print("❌ JWT_SECRET is using default placeholder value. Please generate a secure secret.")
        return False
    
    print(f"✅ JWT_SECRET is properly configured ({len(jwt_secret)} chars)")
    return True

def main():
    """Main setup function."""
    print("🔒 Klerno Labs Security Setup")
    print("=" * 40)
    
    # Create .env file if it doesn't exist
    create_env_file()
    
    # Load environment variables from .env if it exists
    from dotenv import load_dotenv
    load_dotenv()
    
    # Validate JWT secret
    jwt_valid = validate_jwt_secret()
    
    if jwt_valid:
        print("\n🎉 Security setup completed successfully!")
        print("You can now run the application safely.")
    else:
        print("\n⚠️  Security setup needs attention.")
        print("Please review your .env file and ensure all secrets are properly configured.")
        
        # Generate a new JWT secret for immediate use
        new_secret = secrets.token_hex(32)
        print(f"\nGenerated JWT_SECRET for immediate use:")
        print(f"JWT_SECRET={new_secret}")
        print("\nTo use this secret, add it to your .env file or export it as an environment variable:")
        print(f"export JWT_SECRET={new_secret}")

if __name__ == "__main__":
    main()