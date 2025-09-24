"""
Klerno Labs - Enterprise Edition Main Application
TOP 0.1% Application with Enterprise Features Integration
"""

from __future__ import annotations

import io
import logging
import sys
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

try:
    from starlette.middleware.sessions import SessionMiddleware

    _has_session_middleware = True
except Exception:  # itsdangerous may be missing in minimal envs
    SessionMiddleware = None
    _has_session_middleware = False

try:
    from app import admin, auth, store
except Exception:
    # In minimal preview/test environments optional app submodules may
    # fail to import due to missing dependencies (jwt, itsdangerous, etc.).
    # Defer to shim registration later.
    admin = None
    auth = None
    store = None

# Import clean app components
from app.settings import settings

# Import enterprise configuration
from enterprise_config import get_config, get_enabled_features, is_enterprise_enabled

# Configure logging - add a file handler so startup failures are always recorded
LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "enterprise.log"

logger = logging.getLogger("klerno.enterprise")
logger.setLevel(logging.DEBUG)

# Console handler: ensure console stream is UTF-8 encoded on Windows
try:
    console_stream = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", line_buffering=True
    )
    ch = logging.StreamHandler(stream=console_stream)
except Exception:
    # Fallback to default stream handler
    ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(ch)

# File handler (rotating not necessary for small local logs)
fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
fh.setLevel(logging.DEBUG)
fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
logger.addHandler(fh)

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
    "guardian": False,
}

# Keep a record of loaded enterprise modules to avoid 'assigned but never used' warnings
_loaded_enterprise_modules: list[str] = []


def initialize_enterprise_features():
    """Initialize enterprise features based on configuration."""
    config = get_config()

    # Ensure features is initialized
    if config.features is None:
        from enterprise_config import EnterpriseFeatures

        config.features = EnterpriseFeatures()

    if not config.enterprise_mode:
        logger.info("Running in SIMPLE mode - Enterprise features disabled")
        return

    logger.info("Initializing ENTERPRISE features...")

    try:
        # Check each enterprise module
        feature_count = 0

        # Enterprise Monitoring
        if config.features.monitoring_enabled:
            try:
                import enterprise_monitoring as _enterprise_monitoring

                ENTERPRISE_FEATURES["monitoring"] = True
                _loaded_enterprise_modules.append(_enterprise_monitoring.__name__)
                feature_count += 1
                logger.info("Enterprise Monitoring System available")
            except ImportError:
                logger.warning("Enterprise Monitoring module not available")

        # Advanced Security
        if config.features.security_hardening:
            try:
                import enterprise_security as _enterprise_security

                ENTERPRISE_FEATURES["security"] = True
                _loaded_enterprise_modules.append(_enterprise_security.__name__)
                feature_count += 1
                logger.info("Advanced Security Hardening available")
            except ImportError:
                logger.warning("Enterprise Security module not available")

        # Business Analytics
        if config.features.analytics_enabled:
            try:
                import enterprise_analytics as _enterprise_analytics

                ENTERPRISE_FEATURES["analytics"] = True
                _loaded_enterprise_modules.append(_enterprise_analytics.__name__)
                feature_count += 1
                logger.info("Enterprise Analytics System available")
            except ImportError:
                logger.warning("Enterprise Analytics module not available")

        # Financial Compliance
        if config.features.financial_compliance:
            try:
                import financial_compliance as _financial_compliance

                ENTERPRISE_FEATURES["compliance"] = True
                _loaded_enterprise_modules.append(_financial_compliance.__name__)
                feature_count += 1
                logger.info("ISO20022 Financial Compliance available")
            except ImportError:
                logger.warning("Financial Compliance module not available")

        # AI Processing
        if config.features.ai_processing:
            try:
                import ai_processor as _ai_processor

                ENTERPRISE_FEATURES["ai"] = True
                _loaded_enterprise_modules.append(_ai_processor.__name__)
                feature_count += 1
                logger.info("AI Processing System available")
            except ImportError:
                logger.warning("AI Processing module not available")

        # Guardian Protection
        if config.features.guardian_protection:
            try:
                import guardian as _guardian

                ENTERPRISE_FEATURES["guardian"] = True
                _loaded_enterprise_modules.append(_guardian.__name__)
                feature_count += 1
                logger.info("Guardian Protection System available")
            except ImportError:
                logger.warning("Guardian Protection module not available")

        logger.info(f"ENTERPRISE MODE: {feature_count} features available")

    except Exception as e:
        logger.error(f"Enterprise initialization error: {e}")


# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Klerno Labs Enterprise Platform...")
    # Early diagnostic print to ensure we see something in stdout when the
    # process starts. This helps in environments where output is suppressed.
    print("[DIAG] enterprise_main_v2: lifespan start")

    # Initialize clean app database if the store module is available
    if store is not None and getattr(store, "init_db", None) is not None:
        try:
            store.init_db()
            logger.info("Clean app database initialized")
        except Exception as e:
            logger.warning(f"store.init_db() failed: {e}")
    else:
        logger.warning("store module not available; skipping DB initialization")

    # Initialize enterprise features
    initialize_enterprise_features()

    logger.info("Klerno Labs Enterprise Platform started successfully!")
    logger.info(f"Mode: {'ENTERPRISE' if is_enterprise_enabled() else 'SIMPLE'}")

    yield

    # Shutdown
    logger.info("Shutting down Klerno Labs Enterprise Platform...")


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

# Add session middleware if available
if _has_session_middleware and SessionMiddleware is not None:
    app.add_middleware(SessionMiddleware, secret_key=settings.jwt_secret)
else:
    logger.warning(
        "SessionMiddleware unavailable; skipping session middleware registration"
    )

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Some templates and older front-end paths request assets at root-level
# paths like `/css/...`, `/js/...`, `/images/...` and `/vendor/...`.
# Provide lightweight mounts to the appropriate subfolders so both
# `/static/...` and the shorter paths resolve.
app.mount("/css", StaticFiles(directory="static/css"), name="css")
app.mount("/js", StaticFiles(directory="static/js"), name="js")
app.mount("/images", StaticFiles(directory="static/images"), name="images")
app.mount("/vendor", StaticFiles(directory="static/vendor"), name="vendor")


# Simple monitoring middleware
@app.middleware("http")
async def simple_monitoring_middleware(request: Request, call_next):
    """Simple monitoring middleware for basic metrics."""
    start_time = datetime.now()

    response = await call_next(request)

    if ENTERPRISE_FEATURES["monitoring"]:
        try:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(
                f"{request.method} {request.url.path} - {response.status_code} - {duration:.2f}ms"
            )
        except Exception as e:
            logger.error(f"Monitoring error: {e}")

    return response


# Security headers middleware - small, non-breaking defaults to improve app security
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    try:
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
        response.headers["Permissions-Policy"] = "geolocation=()"
        # A reasonably strict CSP for the local app; adjust for external assets in production
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; "
            "script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
        )
    except Exception:
        # Do not let header setting break the response
        pass
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
        "enterprise_modules": ENTERPRISE_FEATURES,
        # include environment string to ensure `config` is used by analyzer
        "environment": getattr(config, "environment", ""),
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
            "enterprise_mode": config.enterprise_mode,
        },
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
        "config": get_config().get_feature_summary(),
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
    # TemplateResponse expects (template_name, context)
    return templates.TemplateResponse("landing.html", context)


# Aliases for legacy template paths: some templates link to `/signup` and
# `/login` (without the `/auth` prefix). Provide top-level aliases that
# delegate to the `app.auth` handlers so both paths work.


@app.get("/signup", response_class=HTMLResponse)
async def signup_alias(request: Request):
    if auth is not None and getattr(auth, "signup_page", None) is not None:
        return auth.signup_page(request)

    templates.env.globals["url_path_for"] = request.app.url_path_for
    return templates.TemplateResponse(
        "signup_enhanced.html", {"request": request, "app_env": "dev"}
    )


@app.get("/login", response_class=HTMLResponse)
async def login_alias(request: Request):
    if auth is not None and getattr(auth, "login_page", None) is not None:
        return auth.login_page(request)

    templates.env.globals["url_path_for"] = request.app.url_path_for
    return templates.TemplateResponse(
        "login_enhanced.html", {"request": request, "error": None, "app_env": "dev"}
    )


# Provide a top-level offline.html route that some service workers expect
@app.get("/offline.html")
async def offline_page():
    # Serve the static offline page if present
    offline_path = Path("static/offline.html")
    if offline_path.exists():
        from fastapi.responses import FileResponse

        return FileResponse(str(offline_path), media_type="text/html")
    raise HTTPException(status_code=404, detail="offline.html not found")


# Include auth + admin routes. Routers already define their own prefixes
# (e.g. `auth.router` uses prefix="/auth"). If a module failed to import
# (e.g. optional dependency missing) register a lightweight shim router
# so the app remains usable in preview mode.
from fastapi import APIRouter


def _register_auth_router():
    if auth is not None and getattr(auth, "router", None) is not None:
        app.include_router(auth.router)
        return

    logger.warning("auth module not available - registering shim auth routes")
    shim = APIRouter(prefix="/auth", tags=["auth"])

    @shim.get("/signup", response_class=HTMLResponse)
    def _shim_signup(request: Request):
        templates.env.globals["url_path_for"] = request.app.url_path_for
        return templates.TemplateResponse(
            "signup_enhanced.html", {"request": request, "app_env": "dev"}
        )

    @shim.get("/login", response_class=HTMLResponse)
    def _shim_login(request: Request, error: str | None = None):
        templates.env.globals["url_path_for"] = request.app.url_path_for
        return templates.TemplateResponse(
            "login_enhanced.html",
            {"request": request, "error": error, "app_env": "dev"},
        )

    app.include_router(shim)


def _register_admin_router():
    if admin is not None and getattr(admin, "router", None) is not None:
        app.include_router(admin.router)
        return

    logger.warning("admin module not available - registering shim admin routes")
    shim = APIRouter(prefix="/admin", tags=["admin"])

    @shim.get("/", response_class=HTMLResponse)
    def _shim_admin_home(request: Request):
        return templates.TemplateResponse(
            "admin.html", {"request": request, "title": "Admin"}
        )

    app.include_router(shim)


_register_auth_router()
_register_admin_router()


if __name__ == "__main__":
    import uvicorn

    config = get_config()

    # Log startup banner
    print("=" * 80)
    print("KLERNO LABS ENTERPRISE EDITION")
    print("   TOP 0.1% Advanced Transaction Analysis Platform")
    print("=" * 80)
    print(f"Mode: {'ENTERPRISE' if config.enterprise_mode else 'SIMPLE'}")
    print(f"Environment: {config.environment}")
    print(f"Features configured: {len(get_enabled_features())}")
    print("=" * 80)

    # Start server with protective try/except to ensure we log any startup
    # exception to the enterprise log file for offline diagnostics.
    try:
        print("[DIAG] Starting uvicorn...")
        uvicorn.run(
            "enterprise_main_v2:app",
            host="127.0.0.1",
            port=8002,  # Use different port for enterprise
            reload=config.debug_mode,
            log_level="info" if not config.debug_mode else "debug",
        )
    except Exception as e:
        # Best-effort: write exception to log file
        try:
            logger.exception("Failed to start uvicorn: %s", e)
            with open(LOG_FILE, "a", encoding="utf-8") as fh:
                fh.write("\n=== STARTUP EXCEPTION ===\n")
                import traceback

                fh.write(traceback.format_exc())
                fh.write("\n=== END STARTUP EXCEPTION ===\n")
        except Exception:
            # If logging to file fails, print to stdout as a last resort
            print("Failed to write startup exception to log file")
            import traceback

            traceback.print_exc()
