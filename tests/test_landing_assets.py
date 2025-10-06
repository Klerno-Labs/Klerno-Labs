from fastapi.testclient import TestClient

from app.main import app


def test_landing_page_and_assets() -> None:
    client = TestClient(app)
    # Landing route should render
    r = client.get("/")
    assert r.status_code == 200

    # Critical CSS
    r = client.get("/static/css/design-system.css")
    assert r.status_code == 200
    assert "--color-text-primary" in r.text

    # Hero image referenced by landing
    r = client.get("/static/images/hero-bg.jpg")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("image/")

    # Manifest should load and have at least one icon
    r = client.get("/static/manifest.json")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get("icons"), list) and len(data["icons"]) >= 1

    # Favicon/svg icon exists (we point manifest to it)
    r = client.get("/static/icons/favicon.svg")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("image/")
