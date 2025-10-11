from fastapi.testclient import TestClient

from app.main import app


def test_landing_contains_klerno():
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Klerno" in resp.text
