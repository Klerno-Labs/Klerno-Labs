#!/usr/bin/env python3
"""
Klerno Labs Server Management Tool
Complete server lifecycle management with health monitoring
"""

import argparse
import os
import sys
import time
import signal
import subprocess
import requests
import json
from pathlib import Path
from datetime import datetime
import psutil

class KlernoServerManager:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.pid_file = self.base_dir / "server.pid"
        self.log_file = self.base_dir / "server.log"
        self.server_url = "http://127.0.0.1:8000"
        self.endpoints = {
            "health": "/healthz",
            "api_health": "/health", 
            "metrics": "/metrics",
            "docs": "/docs",
            "redoc": "/redoc",
            "admin": "/admin/dashboard"
        }
        
    def setup_environment(self):
        """Ensure proper environment setup"""
        env_file = self.base_dir / ".env"
        if not env_file.exists():
            print("⚠️  No .env file found - creating with default values...")
            with open(env_file, "w") as f:
                f.write("JWT_SECRET=your-super-secret-jwt-key-here-make-it-very-long-and-secure-64-chars\n")
                f.write("SECRET_KEY=your-secret-key-for-session-management-56-characters\n")
                f.write("APP_ENV=dev\n")
                f.write("PORT=8000\n")
        
        # Set environment variables
        import dotenv
        dotenv.load_dotenv(env_file)
        
    def get_server_pid(self):
        """Get the PID of the running server"""
        if self.pid_file.exists():
            try:
                with open(self.pid_file, "r") as f:
                    pid = int(f.read().strip())
                # Check if process is actually running
                if psutil.pid_exists(pid):
                    proc = psutil.Process(pid)
                    if "python" in proc.name().lower():
                        return pid
            except (ValueError, psutil.NoSuchProcess):
                pass
        return None
    
    def save_server_pid(self, pid):
        """Save server PID to file"""
        with open(self.pid_file, "w") as f:
            f.write(str(pid))
    
    def is_server_running(self):
        """Check if server is responding"""
        try:
            response = requests.get(f"{self.server_url}/healthz", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def start_server(self, background=True):
        """Start the Klerno Labs server"""
        print("🚀 Starting Klerno Labs server...")
        
        # Setup environment
        self.setup_environment()
        
        # Check if already running
        if self.is_server_running():
            print("✅ Server is already running!")
            self.status()
            return True
        
        try:
            if background:
                # Start server in background
                with open(self.log_file, "w") as log:
                    process = subprocess.Popen([
                        sys.executable, "-m", "uvicorn", "app.main:app",
                        "--host", "0.0.0.0",
                        "--port", "8000",
                        "--reload"
                    ], stdout=log, stderr=subprocess.STDOUT, cwd=self.base_dir)
                
                self.save_server_pid(process.pid)
                print(f"📋 Server started with PID: {process.pid}")
                
                # Wait for server to start
                print("⏳ Waiting for server to start...")
                for i in range(30):
                    if self.is_server_running():
                        print("✅ Server started successfully!")
                        return True
                    time.sleep(1)
                    print(f"   Checking startup... ({i+1}/30)")
                
                print("❌ Server failed to start properly")
                return False
            else:
                # Start server in foreground
                os.execvp(sys.executable, [
                    sys.executable, "-m", "uvicorn", "app.main:app",
                    "--host", "0.0.0.0",
                    "--port", "8000",
                    "--reload"
                ])
        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            return False
    
    def stop_server(self):
        """Stop the Klerno Labs server"""
        print("⏹️  Stopping Klerno Labs server...")
        
        pid = self.get_server_pid()
        if not pid:
            print("ℹ️  No server PID found")
            return True
        
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            
            # Wait for graceful shutdown
            for _ in range(10):
                if not proc.is_running():
                    break
                time.sleep(0.5)
            
            # Force kill if still running
            if proc.is_running():
                proc.kill()
                
            # Clean up PID file
            if self.pid_file.exists():
                self.pid_file.unlink()
                
            print("✅ Server stopped successfully")
            return True
        except psutil.NoSuchProcess:
            print("ℹ️  Server process not found")
            if self.pid_file.exists():
                self.pid_file.unlink()
            return True
        except Exception as e:
            print(f"❌ Failed to stop server: {e}")
            return False
    
    def restart_server(self):
        """Restart the server"""
        print("🔄 Restarting server...")
        self.stop_server()
        time.sleep(2)
        return self.start_server()
    
    def test_endpoints(self):
        """Test all server endpoints"""
        print("🔍 Testing server endpoints...")
        
        if not self.is_server_running():
            print("❌ Server is not running!")
            return False
        
        results = {}
        for name, endpoint in self.endpoints.items():
            try:
                start_time = time.time()
                response = requests.get(f"{self.server_url}{endpoint}", timeout=10)
                duration = (time.time() - start_time) * 1000
                
                results[name] = {
                    "status": response.status_code,
                    "duration_ms": round(duration, 2),
                    "success": response.status_code < 400
                }
                
                status_icon = "✅" if response.status_code < 400 else "❌"
                print(f"  {status_icon} {name:12} [{response.status_code}] {duration:.2f}ms - {endpoint}")
                
            except requests.RequestException as e:
                results[name] = {
                    "status": "error",
                    "error": str(e),
                    "success": False
                }
                print(f"  ❌ {name:12} [ERROR] - {endpoint} ({e})")
        
        # Summary
        successful = sum(1 for r in results.values() if r["success"])
        total = len(results)
        print(f"\n📊 Endpoint Test Results: {successful}/{total} successful")
        
        return successful == total
    
    def status(self):
        """Show detailed server status"""
        print("📋 Klerno Labs Server Status")
        print("=" * 50)
        
        # Server status
        is_running = self.is_server_running()
        status_icon = "✅" if is_running else "❌"
        print(f"Server Status: {status_icon} {'Running' if is_running else 'Not Running'}")
        
        # PID information
        pid = self.get_server_pid()
        if pid:
            try:
                proc = psutil.Process(pid)
                cpu_percent = proc.cpu_percent()
                memory_info = proc.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                
                print(f"Process PID:   {pid}")
                print(f"CPU Usage:     {cpu_percent:.1f}%")
                print(f"Memory Usage:  {memory_mb:.1f} MB")
                print(f"Start Time:    {datetime.fromtimestamp(proc.create_time()).strftime('%Y-%m-%d %H:%M:%S')}")
            except psutil.NoSuchProcess:
                print(f"Process PID:   {pid} (not found)")
        else:
            print("Process PID:   Not available")
        
        print(f"Server URL:    {self.server_url}")
        
        # Log file info
        if self.log_file.exists():
            log_size = self.log_file.stat().st_size / 1024
            print(f"Log File:      {self.log_file} ({log_size:.1f} KB)")
        else:
            print("Log File:      Not found")
        
        print("\n" + "=" * 50)
        
        if is_running:
            self.test_endpoints()
    
    def show_logs(self, lines=50):
        """Show recent server logs"""
        if not self.log_file.exists():
            print("❌ Log file not found")
            return
        
        print(f"📄 Last {lines} lines of server logs:")
        print("=" * 50)
        
        try:
            with open(self.log_file, "r") as f:
                log_lines = f.readlines()
                for line in log_lines[-lines:]:
                    print(line.rstrip())
        except Exception as e:
            print(f"❌ Failed to read logs: {e}")

def main():
    parser = argparse.ArgumentParser(description="Klerno Labs Server Manager")
    parser.add_argument("command", choices=["start", "stop", "restart", "status", "test", "logs"],
                       help="Command to execute")
    parser.add_argument("--foreground", action="store_true", help="Start server in foreground")
    parser.add_argument("--lines", type=int, default=50, help="Number of log lines to show")
    
    args = parser.parse_args()
    manager = KlernoServerManager()
    
    if args.command == "start":
        manager.start_server(background=not args.foreground)
    elif args.command == "stop":
        manager.stop_server()
    elif args.command == "restart":
        manager.restart_server()
    elif args.command == "status":
        manager.status()
    elif args.command == "test":
        manager.test_endpoints()
    elif args.command == "logs":
        manager.show_logs(args.lines)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️  Operation interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)