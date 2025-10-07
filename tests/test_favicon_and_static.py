from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_favicon_served_with_cache_headers(tmp_path, monkeypatch):
    # Point static path for this test to ensure known file exists
    # The operational router uses static/klerno-logo.png relative to CWD
    # Ensure file exists at that path
    static_dir = Path("static")
    static_dir.mkdir(parents=True, exist_ok=True)
    icon_path = static_dir / "klerno-logo.png"
    icon_path.write_bytes(b"fakepngbytes")

    resp = client.get("/favicon.ico", headers={"If-None-Match": '"invalid"'})
    assert resp.status_code in (200, 304)
    assert "ETag" in resp.headers
    assert "Cache-Control" in resp.headers

    # Verify 304 behavior on matching ETag
    etag = resp.headers.get("ETag")
    resp2 = client.get("/favicon.ico", headers={"If-None-Match": etag})
    assert resp2.status_code == 304


def test_docs_available():
    # Swagger UI should be available
    resp = client.get("/docs")
    assert resp.status_code == 200
    assert b"Swagger UI" in resp.content or b"swagger-ui" in resp.content


@pytest.mark.integration
def test_neon_proxy_reachable_without_token(monkeypatch):
    # Configure a fake Neon Data API URL so the route constructs a URL
    monkeypatch.setenv("VITE_NEON_DATA_API_URL", "https://example.invalid")
    r = client.get("/api/neon/notes")
    # Should not be 404; can be 500 due to connection error or 401 if reachable but unauthorized
    assert r.status_code in (500, 401, 400)
