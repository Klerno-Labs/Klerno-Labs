from http import HTTPStatus

from starlette.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_token_status_missing_env(monkeypatch):
    monkeypatch.delenv("NEON_API_KEY", raising=False)
    monkeypatch.delenv("VITE_NEON_DATA_API_URL", raising=False)
    monkeypatch.delenv("NEON_DATA_API_URL", raising=False)

    r = client.get("/api/neon/token-status")
    assert r.status_code == HTTPStatus.OK
    data = r.json()
    assert data["source"] == "missing"
    assert data["base_url_configured"] is False
    assert data["is_jwt"] is False


def test_token_status_with_non_jwt_token(monkeypatch):
    monkeypatch.setenv("NEON_API_KEY", "not-a-jwt-token")
    monkeypatch.setenv("VITE_NEON_DATA_API_URL", "https://example.invalid")

    r = client.get("/api/neon/token-status")
    assert r.status_code == HTTPStatus.OK
    data = r.json()
    assert data["source"] == "env"
    assert data["base_url_configured"] is True
    assert data["is_jwt"] is False
    assert "claims" not in data


def test_token_status_with_authorization_header(monkeypatch):
    # A minimalistic but valid-looking JWT (header.payload.signature)
    # We'll encode a tiny payload with required fields; signature not verified by our endpoint.
    import base64
    import json

    def b64url(s: bytes) -> str:
        return base64.urlsafe_b64encode(s).decode().rstrip("=")

    header = b64url(json.dumps({"alg": "none"}).encode())
    payload = b64url(
        json.dumps(
            {
                "iss": "https://issuer.example",
                "aud": "project-id",
                "sub": "user-id",
                "role": "authenticated",
                "exp": 9999999999,
                "iat": 1111111111,
            }
        ).encode()
    )
    token = f"{header}.{payload}.sig"

    r = client.get(
        "/api/neon/token-status", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == HTTPStatus.OK
    data = r.json()
    assert data["source"] == "header"
    assert data["is_jwt"] is True
    assert data["claims"]["iss"] == "https://issuer.example"
    assert data["claims"]["aud"] == "project-id"
    assert data["claims"]["sub"] == "user-id"
    assert data["claims"]["role"] == "authenticated"
    assert data["claims"]["exp"] == 9999999999
    assert data["claims"]["iat"] == 1111111111
