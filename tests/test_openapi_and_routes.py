from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_openapi_schema_valid_json():
    r = client.get("/openapi.json")
    assert r.status_code == 200
    data = r.json()
    # Minimal structural checks
    assert isinstance(data, dict)
    assert data.get("openapi", "").startswith("3.")
    assert "paths" in data


def test_static_assets_exist_and_serve_index():
    # Ensure key static assets and templates exist
    assert Path("templates/landing-professional.html").exists()
    assert Path("static/css").exists()
    # Landing page served
    r = client.get("/")
    assert r.status_code == 200
    assert any(x in r.text for x in ("Klerno", "Landing", "Welcome"))


def test_csp_report_endpoint_accepts_payload():
    payload = {"csp-report": {"effectiveDirective": "script-src"}}
    r = client.post("/csp/report", json=payload)
    assert r.status_code == 200
    assert r.json().get("ok") is True


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/health",
        "/healthz",
        "/status",
        "/status/details",
        "/ready",
        "/docs",
        "/favicon.ico",
    ],
)
def test_core_get_routes_are_reachable(path: str):
    r = client.get(path)
    # ready can be 200 or 503 depending on ephemeral DB state, both are fine
    if path == "/ready":
        assert r.status_code in (200, 503)
    else:
        # favicon may return 200 or 304
        if path == "/favicon.ico":
            assert r.status_code in (200, 304)
        else:
            assert r.status_code == 200
