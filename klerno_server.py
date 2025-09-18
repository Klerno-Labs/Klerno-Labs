#!/usr/bin/env python3
"""
Klerno Labs - Production Ready Server
Reliable startup script with health monitoring.
"""
import os
import time
import uvicorn
import requests
import subprocess
import sys
from pathlib import Path

class KlernoServer:
    def __init__(self):
        self.host = "127.0.0.1"
        self.port = 8000
        self.setup_environment()
        
    def setup_environment(self):
        """Configure environment variables."""
        os.environ["JWT_SECRET"] = "supersecretjwtkey123456789abcdef0123456789abcdef01234567890abcdef"
        os.environ["SECRET_KEY"] = "klerno_labs_secret_key_2025_very_secure_32_chars_minimum"
        os.environ["ADMIN_EMAIL"] = "admin@klerno.com"
        os.environ["ADMIN_PASSWORD"] = "SecureAdminPass123!"
        os.environ["APP_ENV"] = "dev"
        os.environ["DATABASE_URL"] = "sqlite:///./data/klerno.db"
        
    def check_health(self, timeout=5):
        """Check if server is responding."""
        try:
            response = requests.get(f"http://{self.host}:{self.port}/healthz", timeout=timeout)
            return response.status_code == 200
        except:
            return False
            
    def start_background(self):
        """Start server in background process."""
        cmd = [
            sys.executable, "-c", 
            f"""
import os
import uvicorn

# Set environment
os.environ["JWT_SECRET"] = "{os.environ['JWT_SECRET']}"
os.environ["SECRET_KEY"] = "{os.environ['SECRET_KEY']}"
os.environ["ADMIN_EMAIL"] = "{os.environ['ADMIN_EMAIL']}"
os.environ["ADMIN_PASSWORD"] = "{os.environ['ADMIN_PASSWORD']}"
os.environ["APP_ENV"] = "{os.environ['APP_ENV']}"
os.environ["DATABASE_URL"] = "{os.environ['DATABASE_URL']}"

# Start server
uvicorn.run("app.main:app", host="{self.host}", port={self.port}, reload=False)
"""
        ]
        
        print("🚀 Starting Klerno Labs server in background...")
        process = subprocess.Popen(cmd, cwd=Path.cwd())
        
        # Wait for startup
        print("⏳ Waiting for server to start...")
        for i in range(30):  # 30 second timeout
            time.sleep(1)
            if self.check_health():
                print(f"✅ Server started successfully on http://{self.host}:{self.port}")
                return process
            print(f"   Checking startup... ({i+1}/30)")
            
        print("❌ Server failed to start within 30 seconds")
        process.terminate()
        return None
        
    def start_foreground(self):
        """Start server in foreground."""
        print("🚀 Starting Klerno Labs Server...")
        print(f"🌐 Server will be available at http://{self.host}:{self.port}")
        print("📊 Health check: /healthz")
        print("📖 API docs: /docs (requires authentication)")
        print("⏹️  Press Ctrl+C to stop")
        print("=" * 50)
        
        try:
            uvicorn.run(
                "app.main:app",
                host=self.host,
                port=self.port,
                reload=False,
                log_level="info"
            )
        except KeyboardInterrupt:
            print("\\n⏹️ Server stopped by user")
        except Exception as e:
            print(f"❌ Server error: {e}")
            
    def test_endpoints(self):
        """Test server endpoints."""
        if not self.check_health():
            print("❌ Server not running")
            return False
            
        print("🔍 Testing Klerno Labs Endpoints:")
        print("-" * 40)
        
        endpoints = [
            ("/healthz", "Health Check"),
            ("/health", "Health Status"),
            ("/metrics", "Prometheus Metrics"),
            ("/docs", "API Documentation"),
            ("/redoc", "ReDoc Documentation"),
        ]
        
        working = 0
        for endpoint, description in endpoints:
            try:
                response = requests.get(f"http://{self.host}:{self.port}{endpoint}", timeout=3)
                if response.status_code == 200:
                    status = "✅ WORKING"
                    working += 1
                elif response.status_code == 403:
                    status = "🔐 PROTECTED"
                    working += 1
                else:
                    status = f"⚠️  {response.status_code}"
                print(f"{status} {endpoint} - {description}")
            except Exception as e:
                print(f"❌ FAILED {endpoint} - {description}")
                
        print("-" * 40)
        print(f"📊 Status: {working}/{len(endpoints)} endpoints working")
        return working == len(endpoints)

def main():
    """Main function."""
    import argparse
    parser = argparse.ArgumentParser(description="Klerno Labs Server")
    parser.add_argument("--background", "-b", action="store_true", help="Start in background")
    parser.add_argument("--test", "-t", action="store_true", help="Test endpoints")
    parser.add_argument("--stop", "-s", action="store_true", help="Stop server")
    
    args = parser.parse_args()
    server = KlernoServer()
    
    if args.stop:
        print("⏹️ Stopping server...")
        subprocess.run(["taskkill", "/F", "/IM", "python.exe"], capture_output=True)
        print("✅ Server stopped")
        return
        
    if args.test:
        success = server.test_endpoints()
        sys.exit(0 if success else 1)
        
    if args.background:
        process = server.start_background()
        if process:
            print(f"📋 Server PID: {process.pid}")
            print("🔍 Use --test to check endpoints")
            print("⏹️ Use --stop to stop server")
        sys.exit(0 if process else 1)
    else:
        server.start_foreground()

if __name__ == "__main__":
    main()