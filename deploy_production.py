#!/usr/bin/env python3
"""
Production Deployment Script for Klerno Labs Enterprise Application
Handles production server startup with all enterprise features enabled.
"""

import os
import sys
import uvicorn
import argparse
from pathlib import Path

def setup_production_environment():
    """Set up production environment variables and configuration."""
    
    # Set default environment variables if not already set
    env_defaults = {
        "JWT_SECRET": "production-jwt-secret-key-change-this-in-production-123456789abcdef",
        "ADMIN_EMAIL": "admin@klerno.com",
        "ADMIN_PASSWORD": "SecureAdminPass123!",
        "ENVIRONMENT": "production",
        "LOG_LEVEL": "INFO",
        "WORKERS": "4",
        "TIMEOUT": "120"
    }
    
    for key, default_value in env_defaults.items():
        if not os.getenv(key):
            os.environ[key] = default_value
            print(f"Set default {key}")
    
    # Ensure data directory exists
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    print("✅ Production environment configured")

def validate_production_setup():
    """Validate production setup before starting server."""
    
    print("🔍 Validating production setup...")
    
    # Check critical files exist
    critical_files = ["app/main.py", "requirements.txt"]
    for file_path in critical_files:
        if not Path(file_path).exists():
            print(f"❌ Critical file missing: {file_path}")
            return False
    
    # Check environment variables
    critical_env_vars = ["JWT_SECRET"]
    for var in critical_env_vars:
        if not os.getenv(var):
            print(f"❌ Critical environment variable missing: {var}")
            return False
    
    # Test application import
    try:
        from app.main import app
        print("✅ Application imports successfully")
    except Exception as e:
        print(f"❌ Application import failed: {e}")
        return False
    
    print("✅ Production setup validated")
    return True

def start_production_server(host="0.0.0.0", port=8000, workers=1, debug=False):
    """Start the production server with enterprise features."""
    
    print(f"🚀 Starting Klerno Labs Enterprise Application")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Workers: {workers}")
    print(f"   Debug Mode: {debug}")
    print(f"   Environment: {os.getenv('ENVIRONMENT', 'development')}")
    
    # Configure uvicorn settings
    config = {
        "app": "app.main:app",
        "host": host,
        "port": port,
        "workers": workers if not debug else 1,
        "reload": debug,
        "access_log": True,
        "loop": "auto",
        "http": "auto"
    }
    
    if not debug:
        # Production-specific settings
        config.update({
            "reload": False,
            "access_log": True,
            "server_header": False,
            "date_header": True
        })
    
    try:
        # Start the server
        uvicorn.run(**config)
    except KeyboardInterrupt:
        print("\n🛑 Server shutdown requested")
    except Exception as e:
        print(f"❌ Server error: {e}")
        return 1
    
    return 0

def main():
    """Main deployment script entry point."""
    
    parser = argparse.ArgumentParser(description="Klerno Labs Production Deployment")
    parser.add_argument("--host", default="0.0.0.0", help="Server host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
    parser.add_argument("--workers", type=int, default=1, help="Number of workers (default: 1)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--skip-validation", action="store_true", help="Skip production validation")
    
    args = parser.parse_args()
    
    print("🏭 KLERNO LABS - PRODUCTION DEPLOYMENT")
    print("=" * 50)
    
    # Setup environment
    setup_production_environment()
    
    # Validate setup unless skipped
    if not args.skip_validation:
        if not validate_production_setup():
            print("❌ Production validation failed. Exiting.")
            return 1
    
    # Start server
    return start_production_server(
        host=args.host,
        port=args.port, 
        workers=args.workers,
        debug=args.debug
    )

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)