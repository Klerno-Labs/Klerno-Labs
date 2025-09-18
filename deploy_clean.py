#!/usr/bin/env python3
"""
Production Deployment Script with Clean Startup
Addresses all runtime issues for both local and Render deployment.
"""

import os
import sys
import argparse
import logging
import subprocess
import time
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def ensure_directories():
    """Ensure all required directories exist with proper permissions."""
    directories = [
        "data",
        "logs",
        "static", 
        "templates"
    ]
    
    for directory in directories:
        dir_path = Path(directory)
        dir_path.mkdir(exist_ok=True, parents=True)
        
        # Ensure write permissions (important for Render and OneDrive)
        try:
            test_file = dir_path / ".write_test"
            test_file.touch()
            test_file.unlink()
            logger.info(f"✅ Directory with write access: {directory}")
        except Exception as e:
            logger.warning(f"⚠️  Directory may have permission issues: {directory} - {e}")

def setup_environment():
    """Setup environment variables from .env file."""
    env_file = Path(".env")
    if env_file.exists():
        logger.info("📁 Loading environment from .env file")
        
        # Manual .env loading (works without python-dotenv)
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())
    else:
        logger.warning("⚠️  No .env file found, using environment defaults")
    
    # Set critical defaults
    defaults = {
        "APP_ENV": "development",
        "PORT": "8000", 
        "HOST": "0.0.0.0",
        "WORKERS": "1",
        "LOG_LEVEL": "info",
        "USE_REDIS": "false",
        "USE_MEMCACHED": "false",
        "HEALTHCHECK_PATH": "/healthz",
        "BACKEND_TARGETS": "localhost:8000",
        "DATABASE_URL": "sqlite:///./data/klerno.db"
    }
    
    for key, value in defaults.items():
        os.environ.setdefault(key, value)
        logger.info(f"   {key}={os.environ[key]}")

def initialize_database():
    """Initialize SQLite database."""
    try:
        db_path = os.environ.get("DATABASE_URL", "sqlite:///./data/klerno.db").replace("sqlite:///", "")
        db_file = Path(db_path)
        
        if not db_file.exists():
            logger.info("🔧 Creating SQLite database")
            
            # Import sqlite3 and create basic structure
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Basic tables for application
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            conn.commit()
            conn.close()
            logger.info(f"✅ SQLite database initialized: {db_path}")
        else:
            logger.info(f"✅ SQLite database exists: {db_path}")
            
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

def validate_application():
    """Validate that the application can be imported and started."""
    try:
        # Add app directory to path
        sys.path.insert(0, str(Path(__file__).parent / "app"))
        
        # Test import
        from app.main import app
        logger.info("✅ Application imports successfully")
        
        # Count routes
        route_count = len([r for r in app.routes if hasattr(r, 'path')])
        logger.info(f"✅ Application has {route_count} routes configured")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Application validation failed: {e}")
        return False

def start_production_server(host="0.0.0.0", port=8000, workers=1):
    """Start the production server with proper configuration."""
    
    # Prepare uvicorn command
    cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", str(host),
        "--port", str(port),
        "--workers", str(workers),
        "--log-level", os.environ.get("LOG_LEVEL", "info")
    ]
    
    # Add reload for development
    if os.environ.get("APP_ENV", "development") == "development":
        cmd.append("--reload")
    
    logger.info("🚀 Starting production server...")
    logger.info(f"   Command: {' '.join(cmd)}")
    logger.info(f"   Server will be available at: http://{host}:{port}")
    logger.info(f"   Health check endpoint: http://{host}:{port}/healthz")
    
    try:
        # Start the server
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Server failed to start: {e}")
        raise

def main():
    """Main deployment function."""
    parser = argparse.ArgumentParser(description="Production Deployment Script")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--workers", type=int, default=1, help="Number of workers")
    parser.add_argument("--validate-only", action="store_true", help="Only validate, don't start server")
    
    args = parser.parse_args()
    
    logger.info("🏭 Klerno Labs Production Deployment")
    logger.info("=" * 50)
    
    try:
        # Step 1: Setup environment
        logger.info("1️⃣  Setting up environment...")
        setup_environment()
        
        # Step 2: Ensure directories  
        logger.info("2️⃣  Ensuring directories...")
        ensure_directories()
        
        # Step 3: Initialize database
        logger.info("3️⃣  Initializing database...")
        initialize_database()
        
        # Step 4: Validate application
        logger.info("4️⃣  Validating application...")
        if not validate_application():
            logger.error("❌ Application validation failed")
            return 1
        
        if args.validate_only:
            logger.info("✅ Validation complete - application ready for deployment")
            return 0
        
        # Step 5: Start server
        logger.info("5️⃣  Starting production server...")
        start_production_server(
            host=args.host, 
            port=args.port, 
            workers=args.workers
        )
        
        return 0
        
    except Exception as e:
        logger.error(f"💥 Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())