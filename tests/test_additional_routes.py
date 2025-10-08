from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_dashboard_template_renders():
    # dashboard template exists and renders
    assert Path("templates/dashboard.html").exists()
    r = client.get("/dashboard")
    assert r.status_code == 200
    assert any(x in r.text for x in ("Dashboard", "Klerno", "Analysis"))


def test_admin_users_endpoint_backward_compat():
    # Test that admin endpoint properly requires authentication (security hardening)
    r = client.get("/admin/users")
    assert r.status_code == 401  # Now properly secured

    # Test that the endpoint exists and returns proper structure when authenticated
    # Note: In a real test, you would authenticate first with valid admin credentials
    response_data = r.json()
    assert response_data["error"]["message"] == "Authentication required"


def test_premium_advanced_analytics_exists():
    r = client.get("/premium/advanced-analytics")
    # Ensure reachability: endpoint may enforce paywall (402) or return 200
    assert r.status_code in (200, 402)
    body = r.json()
    assert isinstance(body, dict)
    # If paywalled, an error/detail is present; otherwise an ok flag
    assert ("ok" in body) or ("error" in body or "detail" in body)


@pytest.mark.parametrize(
    "asset",
    [
        "static/klerno-logo.png",
        "static/css",
    ],
)
def test_key_static_assets_present(asset: str):
    assert Path(asset).exists()
