"""
Klerno Labs - Robust Server Startup
Handles timeout issues and provides reliable server startup with proper error handling.
"""

import asyncio
import os
import sys
import signal
import threading
import time
import traceback
from pathlib import Path

# Set up environment first
os.environ.setdefault('JWT_SECRET', 'supersecretjwtkey123456789abcdef0123456789abcdef01234567890abcdef')
os.environ.setdefault('SECRET_KEY', 'klerno_labs_secret_key_2025_very_secure_32_chars_minimum')
os.environ.setdefault('ADMIN_EMAIL', 'admin@klerno.com')
os.environ.setdefault('ADMIN_PASSWORD', 'SecureAdminPass123!')

class RobustServer:
    """Robust server startup with timeout handling."""
    
    def __init__(self):
        self.server = None
        self.should_exit = False
        
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\n[SHUTDOWN] Received signal {signum}, shutting down gracefully...")
        self.should_exit = True
        if self.server:
            self.server.should_exit = True
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self.signal_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, self.signal_handler)
    
    def start_server(self, host="127.0.0.1", port=8000):
        """Start the server with robust error handling."""
        try:
            print("[STARTUP] Klerno Labs Server - Robust Mode")
            print(f"[STARTUP] Starting on {host}:{port}")
            print("[STARTUP] Setting up signal handlers...")
            self.setup_signal_handlers()
            
            print("[STARTUP] Importing application...")
            from app.main import app
            print("[OK] Application imported successfully")
            
            print("[STARTUP] Importing uvicorn...")
            import uvicorn
            print("[OK] Uvicorn imported successfully")
            
            # Configure uvicorn with robust settings
            config = uvicorn.Config(
                app,
                host=host,
                port=port,
                log_level="info",
                access_log=True,
                use_colors=True,
                server_header=False,
                date_header=False,
                # Timeout settings
                timeout_keep_alive=5,
                timeout_notify=30,
                # Disable reload for stability
                reload=False,
                # Single worker for development
                workers=1
            )
            
            print("[STARTUP] Creating server instance...")
            self.server = uvicorn.Server(config)
            
            print("[STARTUP] Starting server...")
            print("=" * 50)
            
            # Run the server
            if sys.version_info >= (3, 7):
                asyncio.run(self.server.serve())
            else:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(self.server.serve())
                
        except KeyboardInterrupt:
            print("\n[SHUTDOWN] Server stopped by user (Ctrl+C)")
        except Exception as e:
            print(f"\n[ERROR] Server error: {e}")
            print("[ERROR] Full traceback:")
            traceback.print_exc()
            return 1
        
        return 0

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Klerno Labs Robust Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    
    args = parser.parse_args()
    
    server = RobustServer()
    exit_code = server.start_server(args.host, args.port)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()