"""Optional Prometheus metrics wiring.

Design goals:
1. Zero impact if `prometheus_client` is not installed.
2. No static type checker noise (everything local & dynamic).
3. Low overhead: light label set; avoid high-cardinality paths.

Also exposes tiny helper functions to record rate-limit allow/deny events.
These are safe no-ops when Prometheus is unavailable or not yet initialized.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from fastapi import APIRouter, FastAPI, Request, Response

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

# Module-level handles initialized by setup_metrics; remain None if unavailable.
_prom_available: bool = False
_registry = None
_req_counter = None
_latency_hist = None
_rl_allow_counter = None
_rl_deny_counter = None
_csp_violation_counter = None
_neon_req_counter = None
_neon_latency_hist = None


def inc_rate_limit_allowed(backend: str = "memory") -> None:
    """Increment the rate-limit 'allowed' counter for the given backend.

    Safe to call regardless of Prometheus availability; becomes a no-op when
    counters are uninitialized.
    """
    try:
        if _rl_allow_counter is not None:
            _rl_allow_counter.labels(backend=backend).inc()
    except Exception:
        # Never let metrics cause functional issues
        pass


def inc_rate_limit_denied(backend: str = "memory") -> None:
    """Increment the rate-limit 'denied' counter for the given backend.

    Safe to call regardless of Prometheus availability; becomes a no-op when
    counters are uninitialized.
    """
    try:
        if _rl_deny_counter is not None:
            _rl_deny_counter.labels(backend=backend).inc()
    except Exception:
        # Never let metrics cause functional issues
        pass


def inc_csp_violation(directive: str = "unknown") -> None:
    """Increment the CSP violation counter for a given directive.

    Keeps label cardinality low by normalizing directive tokens and falling back to
    'unknown' on unexpected values. Safe no-op when Prometheus is unavailable.
    """
    try:
        if not directive:
            directive = "unknown"
        # Normalize common forms like 'script-src-elem'/'script-src' etc.
        base = str(directive).strip().lower()
        if " " in base:
            base = base.split(" ", 1)[0]
        if _csp_violation_counter is not None:
            _csp_violation_counter.labels(directive=base).inc()
    except Exception:
        # Never let metrics cause functional issues
        pass


def setup_metrics(app: FastAPI) -> None:  # pragma: no cover
    # Always expose /metrics; if prometheus_client is unavailable, serve a
    # minimal payload to ensure a 200 response and consistent ops behavior.
    try:
        from prometheus_client import (
            CollectorRegistry,
            Counter,
            Histogram,
            generate_latest,
        )

        prom_available = True
    except Exception:
        prom_available = False

    registry = None
    req_counter = None
    latency_hist = None
    rl_allow = None
    rl_deny = None
    if prom_available:
        registry = CollectorRegistry(auto_describe=True)
        req_counter = Counter(
            "http_requests_total",
            "HTTP requests total",
            labelnames=["method", "path", "status"],
            registry=registry,
        )
        latency_hist = Histogram(
            "http_request_duration_seconds",
            "Request latency seconds",
            labelnames=["method", "path"],
            registry=registry,
        )
        rl_allow = Counter(
            "rate_limit_allowed_total",
            "Requests allowed by the rate limiter",
            labelnames=["backend"],
            registry=registry,
        )
        rl_deny = Counter(
            "rate_limit_denied_total",
            "Requests denied (429) by the rate limiter",
            labelnames=["backend"],
            registry=registry,
        )
        csp_viol = Counter(
            "csp_violations_total",
            "CSP violation reports received",
            labelnames=["directive"],
            registry=registry,
        )
        neon_req = Counter(
            "neon_proxy_requests_total",
            "Neon proxy requests total",
            labelnames=["route", "status"],
            registry=registry,
        )
        neon_lat = Histogram(
            "neon_proxy_duration_seconds",
            "Neon proxy call duration seconds",
            labelnames=["route"],
            registry=registry,
        )

    # Publish to module-level globals for helper functions
    global _prom_available, _registry, _req_counter, _latency_hist, _rl_allow_counter
    global _rl_deny_counter, _csp_violation_counter, _neon_req_counter, _neon_latency_hist
    _prom_available = prom_available
    _registry = registry
    _req_counter = req_counter
    _latency_hist = latency_hist
    _rl_allow_counter = rl_allow
    _rl_deny_counter = rl_deny
    _csp_violation_counter = locals().get("csp_viol") if prom_available else None
    _neon_req_counter = locals().get("neon_req") if prom_available else None
    _neon_latency_hist = locals().get("neon_lat") if prom_available else None

    @app.middleware("http")
    async def _metrics_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start = time.perf_counter()
        response: Response = await call_next(request)
        if prom_available and req_counter and latency_hist and registry:
            elapsed = time.perf_counter() - start
            path = request.url.path
            if path.count("/") > 6:
                path = "/_various"
            try:
                req_counter.labels(
                    request.method,
                    path,
                    str(response.status_code),
                ).inc()
                latency_hist.labels(request.method, path).observe(elapsed)
            except Exception:
                pass
        return response

    # Idempotent: if already registered skip
    if any(getattr(r, "path", None) == "/metrics" for r in app.routes):
        return

    router = APIRouter()

    @router.get("/metrics", include_in_schema=False)
    async def metrics_endpoint() -> Response:
        if prom_available and registry is not None:
            try:
                payload = generate_latest(registry)
                return Response(content=payload, media_type="text/plain; version=0.0.4")
            except Exception:
                return Response(status_code=500)
        # Minimal fallback payload for environments without prometheus_client
        return Response(
            content=b"# Klerno metrics\n# prometheus_client unavailable\n",
            media_type="text/plain",
        )

    app.include_router(router)


def neon_record(route: str, status: int, duration: float) -> None:
    """Record Neon proxy metrics when available.

    Safe no-op if Prometheus is unavailable.
    """
    try:
        if _neon_req_counter is not None:
            _neon_req_counter.labels(route=route, status=str(status)).inc()
        if _neon_latency_hist is not None:
            _neon_latency_hist.labels(route=route).observe(duration)
    except Exception:
        pass
