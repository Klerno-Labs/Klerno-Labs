"""Optional Prometheus metrics wiring.

Design goals:
1. Zero impact if `prometheus_client` is not installed.
2. No static type checker noise (everything local & dynamic).
3. Low overhead: light label set; avoid high-cardinality paths.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from fastapi import APIRouter, Request, Response


def setup_metrics(app) -> None:  # pragma: no cover
    try:
        from prometheus_client import (
            CollectorRegistry,
            Counter,
            Histogram,
            generate_latest,
        )
    except Exception:
        return  # silently skip when library absent

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

    @app.middleware("http")
    async def _metrics_middleware(request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response: Response = await call_next(request)
        elapsed = time.perf_counter() - start
        path = request.url.path
        if path.count("/") > 6:
            path = "/_various"
        try:
            req_counter.labels(request.method, path, str(response.status_code)).inc()
            latency_hist.labels(request.method, path).observe(elapsed)
        except Exception:
            pass
        return response

    # Idempotent: if already registered skip
    if any(r.path == "/metrics" for r in app.routes):
        return

    router = APIRouter()

    @router.get("/metrics", include_in_schema=False)
    async def metrics_endpoint() -> Response:
        try:
            payload = generate_latest(registry)
            return Response(content=payload, media_type="text/plain; version=0.0.4")
        except Exception:
            return Response(status_code=500)

    app.include_router(router)
