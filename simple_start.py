#!/usr/bin/env python3
"""
Simple server startup script.
"""
import os
import uvicorn

# Set environment variables
os.environ["JWT_SECRET"] = "supersecretjwtkey123456789abcdef0123456789abcdef01234567890abcdef"
os.environ["SECRET_KEY"] = "klerno_labs_secret_key_2025_very_secure_32_chars_minimum"
os.environ["ADMIN_EMAIL"] = "admin@klerno.com"
os.environ["ADMIN_PASSWORD"] = "SecureAdminPass123!"

if __name__ == "__main__":
    print("🚀 Starting Klerno Labs Server...")
    print(f"JWT_SECRET: {len(os.environ.get('JWT_SECRET', ''))} chars")
    print(f"SECRET_KEY: {len(os.environ.get('SECRET_KEY', ''))} chars")
    
    try:
        uvicorn.run(
            "app.main:app",
            host="127.0.0.1",
            port=8000,
            reload=False,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n⏹️ Server stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()