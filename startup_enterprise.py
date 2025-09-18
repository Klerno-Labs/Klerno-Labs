#!/usr/bin/env python3
"""
Enterprise Application Startup Script
Initializes all enterprise modules with proper error handling and logging.
"""

import os
import sys
import logging
import asyncio
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

# Configure logging before any imports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/startup.log", mode='a')
    ]
)

logger = logging.getLogger(__name__)

def ensure_directories():
    """Ensure required directories exist."""
    directories = [
        "data",
        "logs", 
        "static",
        "templates"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True, parents=True)
        logger.info(f"✅ Directory ensured: {directory}")

def load_configuration():
    """Load and validate configuration."""
    try:
        from config import settings
        logger.info("✅ Configuration loaded successfully")
        logger.info(f"   Environment: {settings.app_env}")
        logger.info(f"   Port: {settings.port}")
        logger.info(f"   Database: {settings.db_path}")
        logger.info(f"   Health Check: {settings.healthcheck_path}")
        logger.info(f"   Backend Targets: {settings.get_backend_targets()}")
        logger.info(f"   Cache Config: {settings.get_cache_config()}")
        return settings
    except Exception as e:
        logger.error(f"❌ Configuration loading failed: {e}")
        raise

def initialize_enterprise_features(settings):
    """Initialize enterprise features with proper error handling."""
    features_status = {}
    
    # Enterprise Monitoring
    if settings.enable_monitoring:
        try:
            from enterprise_monitoring import EnterpriseMonitoring
            monitoring = EnterpriseMonitoring()
            features_status["monitoring"] = "✅ Enabled"
            logger.info("✅ Enterprise monitoring initialized")
        except Exception as e:
            features_status["monitoring"] = f"⚠️  Warning: {e}"
            logger.warning(f"⚠️  Enterprise monitoring initialization warning: {e}")
    else:
        features_status["monitoring"] = "⏭️  Disabled"
        
    # Performance Optimization
    if settings.enable_performance_optimization:
        try:
            from performance_optimization import PerformanceOptimizer
            optimizer = PerformanceOptimizer()
            features_status["performance"] = "✅ Enabled"
            logger.info("✅ Performance optimization initialized")
        except Exception as e:
            features_status["performance"] = f"⚠️  Warning: {e}"
            logger.warning(f"⚠️  Performance optimization initialization warning: {e}")
    else:
        features_status["performance"] = "⏭️  Disabled"
        
    # Security Hardening
    if settings.enable_security_hardening:
        try:
            from enterprise_security_enhanced import EnhancedSecurityMiddleware
            features_status["security"] = "✅ Enabled"
            logger.info("✅ Enhanced security initialized")
        except Exception as e:
            features_status["security"] = f"⚠️  Warning: {e}"
            logger.warning(f"⚠️  Enhanced security initialization warning: {e}")
    else:
        features_status["security"] = "⏭️  Disabled"
    
    return features_status

def validate_dependencies():
    """Validate critical dependencies."""
    required_packages = [
        "fastapi",
        "uvicorn", 
        "pydantic",
        "sqlite3"
    ]
    
    optional_packages = {
        "redis": "Redis caching",
        "pymemcache": "Memcached caching",
        "uvloop": "High-performance event loop"
    }
    
    # Check required packages
    missing_required = []
    for package in required_packages:
        try:
            __import__(package)
            logger.info(f"✅ Required package: {package}")
        except ImportError:
            missing_required.append(package)
            logger.error(f"❌ Missing required package: {package}")
    
    if missing_required:
        raise ImportError(f"Missing required packages: {missing_required}")
    
    # Check optional packages
    for package, description in optional_packages.items():
        try:
            __import__(package)
            logger.info(f"✅ Optional package: {package} ({description})")
        except ImportError:
            logger.info(f"⏭️  Optional package not installed: {package} ({description})")

def configure_uvloop():
    """Configure uvloop if available and on compatible platform."""
    try:
        if sys.platform != "win32":  # uvloop doesn't support Windows
            import uvloop
            uvloop.install()
            logger.info("✅ uvloop enabled for enhanced performance")
        else:
            logger.info("ℹ️  uvloop not available on Windows - using default event loop")
    except ImportError:
        logger.info("ℹ️  uvloop not installed - using default event loop")

def startup_enterprise_application():
    """Complete enterprise application startup sequence."""
    logger.info("🚀 Starting Klerno Labs Enterprise Application")
    logger.info("=" * 60)
    
    try:
        # Step 1: Ensure directories
        ensure_directories()
        
        # Step 2: Load configuration
        settings = load_configuration()
        
        # Step 3: Validate dependencies
        validate_dependencies()
        
        # Step 4: Configure event loop
        configure_uvloop()
        
        # Step 5: Initialize enterprise features
        features_status = initialize_enterprise_features(settings)
        
        # Step 6: Final status report
        logger.info("=" * 60)
        logger.info("🎉 Enterprise Application Startup Complete")
        logger.info("Enterprise Features Status:")
        for feature, status in features_status.items():
            logger.info(f"   {feature.title()}: {status}")
        
        logger.info(f"Application ready to start on http://{settings.host}:{settings.port}")
        logger.info("Use the following command to start the server:")
        logger.info(f"   uvicorn app.main:app --host {settings.host} --port {settings.port}")
        
        return True
        
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"❌ Enterprise application startup failed: {e}")
        logger.error("Please check the configuration and dependencies")
        return False

if __name__ == "__main__":
    success = startup_enterprise_application()
    sys.exit(0 if success else 1)