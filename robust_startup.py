#!/usr/bin/env python3
"""
Robust server startup script with comprehensive error handling.
"""
import os
import sys
import traceback
import uvicorn
from pathlib import Path

def setup_environment():
    """Setup environment variables."""
    os.environ.setdefault("JWT_SECRET", "supersecretjwtkey123456789abcdef0123456789abcdef01234567890abcdef")
    os.environ.setdefault("SECRET_KEY", "klerno_labs_secret_key_2025_very_secure_32_chars_minimum")
    os.environ.setdefault("ADMIN_EMAIL", "admin@klerno.com")
    os.environ.setdefault("ADMIN_PASSWORD", "SecureAdminPass123!")
    os.environ.setdefault("APP_ENV", "dev")
    os.environ.setdefault("DATABASE_URL", "sqlite:///./data/klerno.db")

def test_app_import():
    """Test if the FastAPI app can be imported."""
    try:
        print("🔍 Testing app import...")
        sys.path.insert(0, str(Path.cwd()))
        from app.main import app
        print(f"✅ App imported successfully")
        print(f"   Type: {type(app)}")
        print(f"   Routes: {len(app.routes)}")
        return app
    except Exception as e:
        print(f"❌ App import failed: {e}")
        traceback.print_exc()
        return None

def start_server(host="127.0.0.1", port=8000, debug=False):
    """Start the uvicorn server with comprehensive error handling."""
    try:
        print("🚀 Starting Klerno Labs Server...")
        print(f"   Host: {host}")
        print(f"   Port: {port}")
        print(f"   Debug: {debug}")
        
        # Test app import first
        app = test_app_import()
        if not app:
            print("❌ Cannot start server - app import failed")
            return False
        
        print("🔧 Starting uvicorn server...")
        
        # Use uvicorn.run with error handling
        config = uvicorn.Config(
            "app.main:app",
            host=host,
            port=port,
            log_level="info" if not debug else "debug",
            reload=False,  # Disable reload to prevent issues
            access_log=True
        )
        
        server = uvicorn.Server(config)
        print(f"✅ Server configured successfully")
        print(f"🌐 Starting server on http://{host}:{port}")
        
        server.run()
        
    except KeyboardInterrupt:
        print("\\n⏹️  Server stopped by user")
        return True
    except Exception as e:
        print(f"❌ Server startup failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Main startup function."""
    print("🔒 Klerno Labs - Robust Server Startup")
    print("=" * 50)
    
    # Setup environment
    setup_environment()
    print("✅ Environment configured")
    
    # Check working directory
    cwd = Path.cwd()
    print(f"📁 Working directory: {cwd}")
    
    # Check if main app file exists
    app_file = cwd / "app" / "main.py"
    if not app_file.exists():
        print(f"❌ App file not found: {app_file}")
        return False
    print(f"✅ App file found: {app_file}")
    
    # Start server
    success = start_server(host="127.0.0.1", port=8000, debug=True)
    
    if success:
        print("✅ Server started successfully")
        return True
    else:
        print("❌ Server failed to start")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)