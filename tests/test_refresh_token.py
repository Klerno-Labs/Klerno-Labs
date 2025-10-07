from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_signup_returns_refresh_token() -> None:
    resp = client.post(
        "/auth/signup/api",
        json={"email": "refreshuser@example.com", "password": "StrongP@ssw0rd!"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["ok"] is True
    assert data["user"]["email"] == "refreshuser@example.com"


def test_login_returns_refresh_token() -> None:
    # User must exist already
    client.post(
        "/auth/signup/api",
        json={"email": "refreshlogin@example.com", "password": "StrongP@ssw0rd!"},
    )
    resp = client.post(
        "/auth/login_api",
        json={"email": "refreshlogin@example.com", "password": "StrongP@ssw0rd!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_refresh_token_rotation() -> None:
    # Signup to get refresh token
    resp = client.post(
        "/auth/signup/api",
        json={"email": "rotuser@example.com", "password": "StrongP@ssw0rd!"},
    )
    refresh = resp.json()["refresh_token"]
    # Use refresh to get new tokens
    resp2 = client.post("/auth/token/refresh", json={"refresh_token": refresh})
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert "access_token" in data2
    assert "refresh_token" in data2
    # Old refresh should now be invalid
    resp3 = client.post("/auth/token/refresh", json={"refresh_token": refresh})
    assert resp3.status_code == 401


def test_refresh_token_revocation() -> None:
    resp = client.post(
        "/auth/signup/api",
        json={"email": "revokeuser@example.com", "password": "StrongP@ssw0rd!"},
    )
    refresh = resp.json()["refresh_token"]
    # Revoke
    resp2 = client.post("/auth/token/revoke", json={"refresh_token": refresh})
    assert resp2.status_code == 204
    # Now refresh should fail
    resp3 = client.post("/auth/token/refresh", json={"refresh_token": refresh})
    assert resp3.status_code == 401
