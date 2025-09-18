#!/usr/bin/env python3
"""
Simple Production Server Test
============================

This script starts the server in a more relaxed security mode for testing
"""

import os
import sys
import uvicorn
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

def start_test_server():
    """Start the server with relaxed security for testing"""
    
    # Set environment variables
    os.environ["JWT_SECRET"] = "supersecretjwtkey123456789abcdef0123456789abcdef01234567890abcdef"
    os.environ["ADMIN_EMAIL"] = "admin@klerno.com"
    os.environ["ADMIN_PASSWORD"] = "SecureAdminPass123!"
    os.environ["ENVIRONMENT"] = "development"  # Use development mode for testing
    os.environ["LOG_LEVEL"] = "INFO"
    
    print("🏭 KLERNO LABS - TEST SERVER")
    print("=" * 50)
    print("Starting server in development mode for testing...")
    print("Environment: development")
    print("Host: 0.0.0.0")
    print("Port: 8000")
    print("=" * 50)
    
    try:
        # Start the server
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            log_level="info",
            reload=False,
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(start_test_server())