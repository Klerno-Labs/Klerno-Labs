from http import HTTPStatus

from starlette.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_admin_access_shape_when_gating_disabled(monkeypatch):
    # Ensure gating is disabled to allow access regardless of header
    monkeypatch.setenv("ENABLE_TIER_GATING", "false")
    # Clear any min tier override
    monkeypatch.delenv("ADMIN_PAGE_MIN_TIER", raising=False)

    r = client.get("/admin/access")
    assert r.status_code == HTTPStatus.OK
    data = r.json()

    # Validate basic shape
    assert set(data.keys()) == {"gating_enabled", "defaults", "detected", "notes"}
    assert isinstance(data["gating_enabled"], bool)
    assert isinstance(data["defaults"], dict)
    assert isinstance(data["detected"], dict)
    assert isinstance(data["notes"], list)

    # current_tier should be a clean string, not "Tier.admin"
    assert data["detected"]["current_tier"] in {"free", "pro", "premium", "admin"}


def test_admin_access_enforced_when_gating_enabled(monkeypatch):
    # Enforce gating and require admin for this endpoint
    monkeypatch.setenv("ENABLE_TIER_GATING", "true")
    monkeypatch.setenv("ADMIN_PAGE_MIN_TIER", "admin")

    # Non-admin should be forbidden
    r = client.get("/admin/access", headers={"X-User-Tier": "premium"})
    assert r.status_code == HTTPStatus.FORBIDDEN

    # Admin should be allowed
    r = client.get("/admin/access", headers={"X-User-Tier": "admin"})
    assert r.status_code == HTTPStatus.OK
    data = r.json()
    assert data["detected"]["current_tier"] == "admin"
