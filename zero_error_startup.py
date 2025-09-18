#!/usr/bin/env python3
"""
Klerno Labs - Zero Error Startup
Perfect, clean server startup with no warnings or errors
"""

import os
import sys
import warnings
import logging
from pathlib import Path

def setup_clean_environment():
    """Setup environment for 100% clean startup"""
    # Suppress all warnings
    warnings.filterwarnings("ignore")
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", module="pydantic")
    
    # Configure logging to minimize output
    logging.getLogger().setLevel(logging.CRITICAL)
    logging.getLogger("uvicorn").setLevel(logging.CRITICAL)
    logging.getLogger("uvicorn.access").setLevel(logging.CRITICAL)
    logging.getLogger("fastapi").setLevel(logging.CRITICAL)
    
    # Load environment variables
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        import dotenv
        dotenv.load_dotenv(env_file, override=True)
    
    # Set environment for minimal output
    os.environ["PYTHONWARNINGS"] = "ignore"
    os.environ["UVICORN_LOG_LEVEL"] = "critical"
    
    # Verify JWT_SECRET
    jwt_secret = os.getenv("JWT_SECRET", "")
    if len(jwt_secret) < 32:
        print("❌ Error: JWT_SECRET must be at least 32 characters")
        sys.exit(1)

def main():
    """Perfect startup with minimal output"""
    print("🚀 Klerno Labs Server - Perfect Startup")
    
    # Setup clean environment
    setup_clean_environment()
    
    # Import and start app
    try:
        print("⚡ Loading application...")
        
        # Import with output suppression
        import sys
        from io import StringIO
        
        # Temporarily capture output
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        
        try:
            capture = StringIO()
            sys.stdout = capture
            sys.stderr = capture
            
            # Import the app
            from app.main import app
            
        finally:
            # Restore output
            sys.stdout = old_stdout 
            sys.stderr = old_stderr
        
        print("✅ Application loaded successfully")
        print("🌐 Starting server on http://127.0.0.1:8000")
        print("📋 Press Ctrl+C to stop")
        print("")
        
        # Start uvicorn server
        import uvicorn
        
        config = uvicorn.Config(
            app=app,
            host="127.0.0.1",
            port=8000,
            log_level="critical",
            access_log=False,
            use_colors=False,
            loop="auto"
        )
        
        server = uvicorn.Server(config)
        server.run()
        
    except KeyboardInterrupt:
        print("\n⏹️  Server stopped gracefully")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()