from http import HTTPStatus

from starlette.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_token_status_requires_admin(monkeypatch):
    # Default: TOKEN_STATUS_MIN_TIER=admin (no env set)
    monkeypatch.delenv("TOKEN_STATUS_MIN_TIER", raising=False)
    monkeypatch.setenv("ENABLE_TIER_GATING", "true")

    # User tier: premium -> should be forbidden
    r = client.get("/api/neon/token-status", headers={"X-User-Tier": "premium"})
    assert r.status_code == HTTPStatus.FORBIDDEN

    # User tier: admin -> allowed
    r = client.get("/api/neon/token-status", headers={"X-User-Tier": "admin"})
    assert r.status_code == HTTPStatus.OK


def test_neon_notes_requires_premium(monkeypatch):
    # Default: NEON_PROXY_MIN_TIER=premium
    monkeypatch.delenv("NEON_PROXY_MIN_TIER", raising=False)
    monkeypatch.setenv("ENABLE_TIER_GATING", "true")
    # Configure fake url to avoid live network
    monkeypatch.setenv("VITE_NEON_DATA_API_URL", "https://example.invalid")

    # User tier: pro -> forbidden
    r = client.get("/api/neon/notes", headers={"X-User-Tier": "pro"})
    assert r.status_code == HTTPStatus.FORBIDDEN

    # User tier: premium -> proxy executes (likely 500 due to fake URL)
    r = client.get("/api/neon/notes", headers={"X-User-Tier": "premium"})
    assert r.status_code in {
        HTTPStatus.INTERNAL_SERVER_ERROR,
        HTTPStatus.UNAUTHORIZED,
        HTTPStatus.BAD_REQUEST,
    }


def test_override_env_to_free(monkeypatch):
    # Lower the bar to free for testing
    monkeypatch.setenv("ENABLE_TIER_GATING", "true")
    monkeypatch.setenv("NEON_PROXY_MIN_TIER", "free")
    monkeypatch.setenv("VITE_NEON_DATA_API_URL", "https://example.invalid")

    r = client.get("/api/neon/paragraphs", headers={"X-User-Tier": "free"})
    assert r.status_code in {
        HTTPStatus.INTERNAL_SERVER_ERROR,
        HTTPStatus.UNAUTHORIZED,
        HTTPStatus.BAD_REQUEST,
    }
