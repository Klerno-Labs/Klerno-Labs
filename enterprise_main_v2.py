"""
Klerno Labs - Enterprise Edition Main Application
TOP 0.1% Application with Enterprise Features Integration
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app import admin, auth, store

# Import clean app components
from app.settings import settings

# Import enterprise configuration
from enterprise_config import get_config, get_enabled_features, is_enterprise_enabled

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Track application startup time
START_TIME = datetime.now(UTC)

# Templates setup
templates = Jinja2Templates(directory="templates")

# Enterprise feature flags
ENTERPRISE_FEATURES = {
    "monitoring": False,
    "security": False,
    "analytics": False,
    "compliance": False,
    "ai": False,
    "guardian": False
}


def initialize_enterprise_features():
    """Initialize enterprise features based on configuration."""
    global ENTERPRISE_FEATURES

    config = get_config()

    # Ensure features is initialized
    if config.features is None:
        from enterprise_config import EnterpriseFeatures
        config.features = EnterpriseFeatures()

    if not config.enterprise_mode:
        logger.info("🏠 Running in SIMPLE mode - Enterprise features disabled")
        return

    logger.info("🚀 Initializing ENTERPRISE features for TOP 0.1% application...")

    try:
        # Check each enterprise module
        feature_count = 0

        # Enterprise Monitoring
        if config.features.monitoring_enabled:
            try:
                import enterprise_monitoring
                ENTERPRISE_FEATURES["monitoring"] = True
                feature_count += 1
                logger.info("✅ Enterprise Monitoring System available")
            except ImportError:
                logger.warning("⚠️  Enterprise Monitoring module not available")

        # Advanced Security
        if config.features.security_hardening:
            try:
                import enterprise_security
                ENTERPRISE_FEATURES["security"] = True
                feature_count += 1
                logger.info("✅ Advanced Security Hardening available")
            except ImportError:
                logger.warning("⚠️  Enterprise Security module not available")

        # Business Analytics
        if config.features.analytics_enabled:
            try:
                import enterprise_analytics
                ENTERPRISE_FEATURES["analytics"] = True
                feature_count += 1
                logger.info("✅ Enterprise Analytics System available")
            except ImportError:
                logger.warning("⚠️  Enterprise Analytics module not available")

        # Financial Compliance
        if config.features.financial_compliance:
            try:
                import financial_compliance
                ENTERPRISE_FEATURES["compliance"] = True
                feature_count += 1
                logger.info("✅ ISO20022 Financial Compliance available")
            except ImportError:
                logger.warning("⚠️  Financial Compliance module not available")

        # AI Processing
        if config.features.ai_processing:
            try:
                import ai_processor
                ENTERPRISE_FEATURES["ai"] = True
                feature_count += 1
                logger.info("✅ AI Processing System available")
            except ImportError:
                logger.warning("⚠️  AI Processing module not available")

        # Guardian Protection
        if config.features.guardian_protection:
            try:
                import guardian
                ENTERPRISE_FEATURES["guardian"] = True
                feature_count += 1
                logger.info("✅ Guardian Protection System available")
            except ImportError:
                logger.warning("⚠️  Guardian Protection module not available")

        logger.info(f"🏆 ENTERPRISE MODE: {feature_count} features available")

    except Exception as e:
        logger.error(f"❌ Enterprise initialization error: {e}")


# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting Klerno Labs Enterprise Platform...")

    # Initialize clean app database
    store.init_db()
    logger.info("✓ Clean app database initialized")

    # Initialize enterprise features
    initialize_enterprise_features()

    logger.info("🎯 Klerno Labs Enterprise Platform started successfully!")
    logger.info(f"💼 Mode: {'ENTERPRISE' if is_enterprise_enabled() else 'SIMPLE'}")

    yield

    # Shutdown
    logger.info("🔄 Shutting down Klerno Labs Enterprise Platform...")


# Create FastAPI application
app = FastAPI(
    title="Klerno Labs Enterprise Edition",
    description="TOP 0.1% Advanced Transaction Analysis Platform with Enterprise Features",
    version="2.0.0-Enterprise",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session middleware
app.add_middleware(SessionMiddleware, secret_key=settings.jwt_secret)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


# Simple monitoring middleware
@app.middleware("http")
async def simple_monitoring_middleware(request: Request, call_next):
    """Simple monitoring middleware for basic metrics."""
    start_time = datetime.now()

    response = await call_next(request)

    if ENTERPRISE_FEATURES["monitoring"]:
        try:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(f"📊 {request.method} {request.url.path} - {response.status_code} - {duration:.2f}ms")
        except Exception as e:
            logger.error(f"Monitoring error: {e}")

    return response


# Health check endpoint
@app.get("/health")
async def health_check():
    """Enterprise health check with detailed system status."""
    config = get_config()

    health_data = {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": "2.0.0-Enterprise",
        "mode": "enterprise" if is_enterprise_enabled() else "simple",
        "uptime_seconds": (datetime.now(UTC) - START_TIME).total_seconds(),
        "features": get_enabled_features(),
        "enterprise_modules": ENTERPRISE_FEATURES
    }

    return health_data


# Enterprise Dashboard endpoint
@app.get("/enterprise/dashboard")
async def enterprise_dashboard():
    """Enterprise dashboard with comprehensive metrics."""
    if not is_enterprise_enabled():
        raise HTTPException(status_code=404, detail="Enterprise features not enabled")

    config = get_config()

    dashboard_data = {
        "timestamp": datetime.now(UTC).isoformat(),
        "features": get_enabled_features(),
        "config": config.get_feature_summary(),
        "enterprise_modules": ENTERPRISE_FEATURES,
        "system_info": {
            "uptime_seconds": (datetime.now(UTC) - START_TIME).total_seconds(),
            "environment": config.environment,
            "enterprise_mode": config.enterprise_mode
        }
    }

    return dashboard_data


# Enterprise Status endpoint
@app.get("/enterprise/status")
async def enterprise_status():
    """Get detailed enterprise feature status."""
    if not is_enterprise_enabled():
        raise HTTPException(status_code=404, detail="Enterprise features not enabled")

    status_data = {
        "enterprise_mode": is_enterprise_enabled(),
        "available_features": ENTERPRISE_FEATURES,
        "enabled_features": get_enabled_features(),
        "config": get_config().get_feature_summary()
    }

    return status_data


# Import routes from clean app
@app.get("/")
async def landing_page(request: Request):
    """Enhanced landing page with enterprise features."""
    context = {
        "request": request,
        "enterprise_mode": is_enterprise_enabled(),
        "features": get_enabled_features(),
        "title": "Klerno Labs Enterprise Edition",
    }
    return templates.TemplateResponse(request, "landing.html", context)


# Include auth routes
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])


if __name__ == "__main__":
    import uvicorn

    config = get_config()

    # Log startup banner
    print("=" * 80)
    print("🚀 KLERNO LABS ENTERPRISE EDITION")
    print("   TOP 0.1% Advanced Transaction Analysis Platform")
    print("=" * 80)
    print(f"💼 Mode: {'ENTERPRISE' if config.enterprise_mode else 'SIMPLE'}")
    print(f"🌍 Environment: {config.environment}")
    print(f"🔧 Features configured: {len(get_enabled_features())}")
    print("=" * 80)

    # Start server
    uvicorn.run(
        "enterprise_main_v2:app",
        host="127.0.0.1",
        port=8002,  # Use different port for enterprise
        reload=config.debug_mode,
        log_level="info" if not config.debug_mode else "debug"
    )
