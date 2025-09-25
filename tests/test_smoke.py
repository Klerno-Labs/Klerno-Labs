from fastapi.testclient import TestClient

from app.main import app


def test_root_returns_html():
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    # landing page should contain a title or header
    assert "Klerno" in resp.text or "Landing" in resp.text or "Welcome" in resp.text


def test_health_ok():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "ok"


from fastapi.testclient import TestClient

import app.main as main_mod
from app import store
from app.security_session import hash_pw


def test_smoke_login(tmp_path, monkeypatch):
    # Use a temporary sqlite DB for isolated test
    dbfile = tmp_path / "test_klerno.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{dbfile}")

    # Re-import store module state by calling init_db through main lifespan
    client = TestClient(main_mod.app)

    # Ensure DB initialized
    store.init_db()

    # Create dev user
    email = "klerno@outlook.com"
    password = "Labs2025"
    pw_hash = hash_pw(password)
    store.create_user(
        email=email, password_hash=pw_hash, role="admin", subscription_active=True
    )

    # Landing page
    r = client.get("/")
    assert r.status_code == 200

    # Login page
    r = client.get("/auth/login")
    assert r.status_code == 200

    # Form login (simulate browser form post)
    r = client.post(
        "/auth/login",
        data={"email": email, "password": password},
        allow_redirects=False,
    )
    assert r.status_code in (200, 302)

    # Check for session cookie
    cookies = r.cookies
    assert "session" in cookies
