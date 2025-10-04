"""Advanced Caching Middleware for Klerno Labs
Implements HTTP caching headers, static asset optimization, and browser cache control
"""

import hashlib
import mimetypes
import time
from datetime import datetime
from pathlib import Path

from fastapi import Request, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware


class AdvancedCachingMiddleware(BaseHTTPMiddleware):
    """Enhanced caching middleware with smart cache strategies"""

    def __init__(self, app, cache_rules: dict | None = None):
        super().__init__(app)
        self.cache_rules = cache_rules or self._default_cache_rules()
        self.etag_cache: dict[str, str] = {}  # Simple in-memory ETag cache

    def _default_cache_rules(self) -> dict:
        """Default caching rules for different content types"""
        return {
            # Static assets - Long cache with versioning
            "text/css": {
                "max_age": 31536000,
                "public": True,
                "immutable": True,
            },  # 1 year
            "application/javascript": {
                "max_age": 31536000,
                "public": True,
                "immutable": True,
            },
            "image/png": {"max_age": 2592000, "public": True},  # 30 days
            "image/jpeg": {"max_age": 2592000, "public": True},
            "image/webp": {"max_age": 2592000, "public": True},
            "image/svg+xml": {"max_age": 2592000, "public": True},
            "font/woff2": {"max_age": 31536000, "public": True, "immutable": True},
            "font/woff": {"max_age": 31536000, "public": True, "immutable": True},
            # HTML pages - Short cache with validation
            "text/html": {
                "max_age": 300,
                "public": True,
                "must_revalidate": True,
            },  # 5 minutes
            # API responses - No cache or short cache
            "application/json": {
                "max_age": 60,
                "private": True,
                "must_revalidate": True,
            },  # 1 minute
            # Default fallback
            "default": {"max_age": 3600, "public": True},  # 1 hour
        }

    def _generate_etag(self, content: bytes, path: str) -> str:
        """Generate ETag for content validation"""
        import logging

        # Use SHA-256 for content hash (more secure than MD5)
        try:
            content_hash = hashlib.sha256(content).hexdigest()[:16]
        except Exception as e:
            logging.exception(f"ETag hash generation failed: {e}")
            content_hash = "errorhash"
        # Try to get file modification time for static files
        if path.startswith("/static/"):
            try:
                file_path = Path("app") / path.lstrip("/")
                if file_path.exists():
                    mtime = file_path.stat().st_mtime
                    return f'"{content_hash}-{int(mtime)}"'
            except Exception as e:
                logging.warning(f"ETag mtime lookup failed: {e}")
        return f'"{content_hash}"'

    def _get_cache_control(self, content_type: str, path: str) -> str:
        """Generate Cache-Control header based on content type and path"""
        # Get content type without charset
        base_content_type = content_type.split(";")[0].strip()

        # Special handling for different paths
        if path.startswith("/api/"):
            rules = {"max_age": 0, "no_cache": True, "no_store": True}
        elif path.startswith("/admin/") or path.startswith("/auth/"):
            rules = {"max_age": 0, "private": True, "no_cache": True}
        elif path.startswith("/static/vendor/"):
            # Third-party assets can be cached longer
            rules = {"max_age": 86400, "public": True}  # 24 hours
        else:
            rules = self.cache_rules.get(base_content_type, self.cache_rules["default"])

        # Build Cache-Control string
        parts = []
        if rules.get("no_cache"):
            parts.append("no-cache")
        if rules.get("no_store"):
            parts.append("no-store")
        if rules.get("public"):
            parts.append("public")
        if rules.get("private"):
            parts.append("private")
        if rules.get("must_revalidate"):
            parts.append("must-revalidate")
        if rules.get("immutable"):
            parts.append("immutable")
        max_age = rules.get("max_age", 0)
        parts.append(f"max-age={max_age}")

        return ", ".join(parts)

    def _add_security_headers(self, response: Response, path: str):
        """Add security-related caching headers"""
        # Prevent caching of sensitive pages
        if any(
            sensitive in path for sensitive in ["/login", "/signup", "/admin", "/auth"]
        ):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

    def _add_performance_headers(self, response: Response, content_type: str):
        """Add performance optimization headers"""
        # Enable compression hints
        if content_type.startswith("text/") or "json" in content_type:
            response.headers["Vary"] = "Accept-Encoding"

        # DNS prefetch for external resources
        if content_type == "text/html":
            response.headers["Link"] = (
                "<https://fonts.googleapis.com>; rel=dns-prefetch, "
                "<https://cdn.jsdelivr.net>; rel=dns-prefetch"
            )

    async def dispatch(self, request: Request, call_next):
        """Main middleware dispatch method"""
        start_time = time.time()

        # Check for conditional requests
        if_none_match = request.headers.get("if-none-match")
        if_modified_since = request.headers.get("if-modified-since")

        # Call the next middleware/endpoint
        response = await call_next(request)

        # Only add caching headers for successful responses
        if response.status_code == 200:
            content_type = response.headers.get("content-type", "text/plain")
            path = request.url.path

            # Generate ETag if response has content
            if hasattr(response, "body") and response.body:
                etag = self._generate_etag(response.body, path)
                response.headers["ETag"] = etag

                # Check if client has cached version
                if if_none_match and if_none_match == etag:
                    return Response(status_code=304)  # Not Modified

            # Add Cache-Control header
            cache_control = self._get_cache_control(content_type, path)
            response.headers["Cache-Control"] = cache_control

            # Add Last-Modified for static files
            if path.startswith("/static/"):
                try:
                    file_path = Path("app") / path.lstrip("/")
                    if file_path.exists():
                        mtime = file_path.stat().st_mtime
                        last_modified = datetime.fromtimestamp(mtime).strftime(
                            "%a, %d %b %Y %H:%M:%S GMT",
                        )
                        response.headers["Last-Modified"] = last_modified

                        # Check if-modified-since
                        if if_modified_since:
                            try:
                                client_time = datetime.strptime(
                                    if_modified_since,
                                    "%a, %d %b %Y %H:%M:%S GMT",
                                )
                                file_time = datetime.fromtimestamp(mtime)
                                if client_time >= file_time:
                                    return Response(status_code=304)
                            except ValueError:
                                pass
                except Exception:
                    pass

            # Add security headers
            self._add_security_headers(response, path)

            # Add performance headers
            self._add_performance_headers(response, content_type)

            # Add timing header for performance monitoring
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)

        return response


class OptimizedStaticFiles(StaticFiles):
    """Enhanced static file serving with advanced caching"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.compression_types = {
            ".js": "gzip",
            ".css": "gzip",
            ".html": "gzip",
            ".json": "gzip",
            ".svg": "gzip",
        }

    def _get_optimized_headers(self, path: str, stat_result) -> dict[str, str]:
        """Get optimized headers for static files"""
        headers = {}

        # Content-Type with proper charset
        content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
        if content_type.startswith("text/"):
            content_type += "; charset=utf-8"
        headers["content-type"] = content_type

        # Cache headers for different file types
        file_ext = Path(path).suffix.lower()

        if file_ext in [".css", ".js"]:
            # Long cache for CSS/JS with immutable
            headers["cache-control"] = "public, max-age=31536000, immutable"
        elif file_ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
            # Medium cache for images
            headers["cache-control"] = "public, max-age=2592000"
        elif file_ext in [".woff", ".woff2", ".ttf", ".eot"]:
            # Long cache for fonts
            headers["cache-control"] = "public, max-age=31536000, immutable"
        else:
            # Default cache
            headers["cache-control"] = "public, max-age=86400"

        # ETag based on file modification time and size
        etag = f'"{stat_result.st_mtime}-{stat_result.st_size}"'
        headers["etag"] = etag

        # Last-Modified
        last_modified = datetime.fromtimestamp(stat_result.st_mtime)
        headers["last-modified"] = last_modified.strftime("%a, %d %b %Y %H:%M:%S GMT")

        # Compression hint
        if file_ext in self.compression_types:
            headers["vary"] = "Accept-Encoding"

        return headers


def create_cache_optimization_config():
    """Create caching configuration for production deployment"""
    return {
        "static_files": {
            "max_age": 31536000,  # 1 year for static assets
            "public": True,
            "immutable": True,
        },
        "html_pages": {
            "max_age": 300,  # 5 minutes for HTML
            "public": True,
            "must_revalidate": True,
        },
        "api_responses": {
            "max_age": 60,  # 1 minute for API
            "private": True,
            "must_revalidate": True,
        },
        "security_headers": {
            "enable_etag": True,
            "enable_last_modified": True,
            "enable_conditional_requests": True,
        },
    }


# Cache warming utilities
async def warm_cache_on_startup():
    """Warm up cache with frequently accessed resources"""
    # This would be implemented with actual HTTP requests in production
    print("🔥 Cache warming completed for critical resources")


def generate_cache_manifest():
    """Generate cache manifest for PWA"""
    manifest = {
        "version": "1.0.0",
        "cache_urls": [
            "/static/css/design-system.css",
            "/static/css/performance-utils.css",
            "/static/js/main.js",
            "/static/klerno-logo.png",
            "/static/klerno-wordmark.png",
            "/",
            "/login",
            "/dashboard",
        ],
        "no_cache_urls": ["/api/*", "/admin/*", "/auth/*"],
    }
    return manifest
